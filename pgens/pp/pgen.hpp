#ifndef PROBLEM_GENERATOR_H
#define PROBLEM_GENERATOR_H

#include "enums.h"
#include "global.h"

#include "arch/kokkos_aliases.h"
#include "utils/error.h"
#include "utils/numeric.h"

#include "archetypes/energy_dist.h"
#include "archetypes/spatial_dist.h"
#include "archetypes/particle_injector.h"
#include "archetypes/problem_generator.h"
#include "archetypes/utils.h"
#include "framework/domain/domain.h"
#include "framework/domain/metadomain.h"

#if defined(MPI_ENABLED)
#include <stdlib.h>
#endif // MPI_ENABLED

namespace user
{
  using namespace ntt;

  template <SimEngine::type S, class M>
  struct UniformDist : public arch::SpatialDistribution<S, M> {
    UniformDist(const M& metric)
      : arch::SpatialDistribution<S, M> { metric } {}

    // to properly scale the number density, the probability should be normalized to 1
    Inline auto operator()(const coord_t<M::Dim>& x_Ph) const -> real_t {
      return ONE; 
    }    
  };
  
  template <SimEngine::type S, class M>
  struct PGen : public arch::ProblemGenerator<S, M>
  {

    // compatibility traits for the problem generator
    static constexpr auto engines = traits::compatible_with<SimEngine::SRPIC>::value;
    static constexpr auto metrics = traits::compatible_with<Metric::Minkowski>::value;
    static constexpr auto dimensions = traits::compatible_with<Dim::_2D>::value;

    // for easy access to variables in the child class
    using arch::ProblemGenerator<S, M>::D;
    using arch::ProblemGenerator<S, M>::C;
    using arch::ProblemGenerator<S, M>::params;

    const real_t temperature1, temperature2;
    const real_t TauBox, dt, Lx, enBath;
    const real_t KNswitch, gammaKN, gammaSwitch;
    const real_t gamma0, ppc;
    const real_t epsilon1; 
    const bool IsIC, IsBW;

    inline PGen(const SimulationParams &p, const Metadomain<S, M> &global_domain)
      : arch::ProblemGenerator<S, M>(p)
      , temperature1 {p.template get<real_t>("setup.temperature")}
      , temperature2 {p.template get<real_t>("setup.temperature2",temperature1)}
      , Lx { global_domain.mesh().extent(in::x1).second -
             global_domain.mesh().extent(in::x1).first }
      , TauBox {p.template get<real_t>("setup.OpticalDepth")}
      , enBath {p.template get<real_t>("setup.photonEnergy")}
	  , ppc  {p.template get<real_t>("particles.ppc0")}
      , gammaKN {1 / (4 * enBath)}
      , KNswitch {p.template get<real_t>("setup.switchToKN",0.1)}
      , gammaSwitch {KNswitch * gammaKN}
      , dt { params.template get<real_t>("algorithms.timestep.dt") }
      , IsIC { params.template get<bool>("setup.IsIC") }
      , IsBW { params.template get<bool>("setup.IsBW") }
      , epsilon1 {params.template get<real_t>("setup.epsilon1") }
      , gamma0 {p.template get<real_t>("setup.gamma0")}{};
    
    inline void InitPrtls(Domain<S, M> &domain)
    {
      const auto ppc_ {ppc};
      const auto epsilon1_ {epsilon1};
      auto& random_pool = domain.random_pool();
      // here I explicitly assume that photons are third species in the toml file 
      
      array_t<std::size_t> phot_ind("phot_ind");
      auto& photons   = domain.species[2];
      auto  offset_phot = photons.npart();
      auto  ux1_phot    = photons.ux1;
      auto  ux2_phot    = photons.ux2;
      auto  ux3_phot    = photons.ux3;
      auto  i1_phot     = photons.i1;
      auto  i2_phot     = photons.i2;
      auto  dx1_phot    = photons.dx1;
      auto  dx2_phot    = photons.dx2;
      auto  weight_phot = photons.weight;
      auto  tag_phot    = photons.tag;
      
      Kokkos::parallel_for(
       	"PhotonInjection",
	domain.mesh.rangeActiveCells(),
	Lambda(index_t i1, index_t i2){
	  auto rand_gen = random_pool.get_state();
	  for (int j = 0; j < int(ppc_); j++){
	    auto phot_p = Kokkos::atomic_fetch_add(&phot_ind(), 1);
	    
	    auto randNum = Random<real_t>(rand_gen);
	    i1_phot(phot_p + offset_phot)  = i1;
	    dx1_phot(phot_p + offset_phot) = randNum;
	    randNum = Random<real_t>(rand_gen);
	    i2_phot(phot_p + offset_phot)  = i2;
	    dx2_phot(phot_p + offset_phot) = randNum;
	    auto angle = constant::TWO_PI * Random<real_t>(rand_gen);
	    auto U = 2*(Random<real_t>(rand_gen)-0.5);
	    ux1_phot(phot_p + offset_phot) = epsilon1_ * math::sqrt(1-U*U) * math::cos(angle); 
	    ux2_phot(phot_p + offset_phot) = epsilon1_ * math::sqrt(1-U*U) * math::sin(angle); 
	    ux3_phot(phot_p + offset_phot) = epsilon1_ * U;
	    tag_phot(phot_p + offset_phot) = ParticleTag::alive; 	
	  }
	  random_pool.free_state(rand_gen); 
	});
      auto phot_ind_h = Kokkos::create_mirror(phot_ind);
      Kokkos::deep_copy(phot_ind_h, phot_ind);
      photons.set_npart(offset_phot + phot_ind_h());
    }
    
    static KOKKOS_INLINE_FUNCTION real_t F(real_t x, real_t y)
    {
      return y * (-y * y / x + x * y * (2 + y) + x * x / 2 + (1 - 2 * y - 2 * y * y) * math::log(x));
    }
    
    static KOKKOS_INLINE_FUNCTION real_t BWfullCS(real_t s, real_t mu)
    {
      auto beta2 = 1.0 - 4.0 / s;
      auto beta = math::sqrt(beta2);
      auto CS = (1.0 - beta2) * (-2.0 * beta * (2.0 - beta2) + (3.0 - beta2 * beta2) * math::log((1.0 + beta) / (1.0 - beta)));
      return (3.0 / 16.0) * CS;
    }

    static KOKKOS_INLINE_FUNCTION real_t dSigma_dO(real_t s, real_t theta)
    {
      auto beta2 = 1.0 - 4.0 / s;
      auto beta4 = beta2 * beta2;
      auto dummy = 4.0 * math::sqrt(beta2) / s;
      auto cos2 = math::cos(theta) * math::cos(theta);
      auto sin2 = math::sin(theta) * math::sin(theta);
      auto sin4 = sin2 * sin2;
      return dummy * math::sin(theta) * (1.0 + 2.0 * beta2 * sin2 - beta4 - beta4 * sin4) 
	/ ((1 - beta2 * cos2) * (1 - beta2 * cos2));
    }

    void CustomPostStep(timestep_t, simtime_t time, Domain<S, M> &domain)
    {
      auto opticalDepthStep{TauBox * dt / Lx};
      auto ThompsonCooling{4.0 * TauBox * enBath * dt / (3.0 * Lx)};
      auto gammaSwitch_{gammaSwitch};
      std::cout << " gamma switch= " << gammaSwitch_ << " optical depth per step= " << opticalDepthStep << std::endl;
      auto enBath_{enBath};
      auto tolerance = 1e-10;
      auto &random_pool = domain.random_pool();
      
      // this is inverse Compton section
      if (IsIC)
	{
	  for (int s = 0; s < 2; s++)
	    {
	      auto &species = domain.species[s];
	      auto ux1 = species.ux1;
	      auto ux2 = species.ux2;
	      auto ux3 = species.ux3;
	      auto i1 = species.i1;
	      auto i2 = species.i2;
	      auto dx1 = species.dx1;
	      auto dx2 = species.dx2;
	      auto weight = species.weight;
	      auto tag = species.tag;

	      // here I explicitly assume that photons are third species in the toml file
	      array_t<std::size_t> phot_ind("phot_ind");
	      auto &photons = domain.species[2];
	      auto offset_phot = photons.npart();
	      auto ux1_phot = photons.ux1;
	      auto ux2_phot = photons.ux2;
	      auto ux3_phot = photons.ux3;
	      auto i1_phot = photons.i1;
	      auto i2_phot = photons.i2;
	      auto dx1_phot = photons.dx1;
	      auto dx2_phot = photons.dx2;
	      auto weight_phot = photons.weight;
	      auto tag_phot = photons.tag;
	      
	      Kokkos::parallel_for(
		"InverseCompton",
		species.rangeActiveParticles(),
		Lambda(index_t p) {
		  if (tag(p) == ParticleTag::dead)
		    {
		      return;
		    }
		  auto px = ux1(p);
		  auto py = ux2(p);
		  auto pz = ux3(p);
		  real_t gamma = math::sqrt(ONE + SQR(px) + SQR(py) + SQR(pz));

		  auto beta_x = px / gamma;
		  auto beta_y = py / gamma;
		  auto beta_z = pz / gamma;
		  
		  // no cooling for very cold particles
		  if (gamma < 1.5)
		    {
		      return;
		    }
		  
		  if (gamma <= gammaSwitch_)
		    {
		      // standard continious IC cooling
		      ux1(p) = px - ThompsonCooling * gamma * gamma * beta_x;
		      ux2(p) = py - ThompsonCooling * gamma * gamma * beta_y;
		      ux3(p) = pz - ThompsonCooling * gamma * gamma * beta_z;
		    }
		  else
		    {
		      // the magic of two-particle QED begins
		      auto rand_gen = random_pool.get_state();
		      auto randNum = Random<real_t>(rand_gen);
		      
		      auto beta = math::sqrt(SQR(beta_x) + SQR(beta_y) + SQR(beta_z));
		      // null collision method
		      if (randNum < opticalDepthStep)
			{
			  // collision might happen, let's generate a fake photon
			  // step 1: generate angle between photon and particle (eqn. 18)
			  
			  randNum = Random<real_t>(rand_gen);
			  
			  auto target = 2 * constant::PI * randNum;
			  auto x = target;
			  
			  real_t f, f_prime, x_new;
			  for (int j = 0; j < 100; j++)
			    {
			      f = x - beta * math::sin(x) - target;
			      f_prime = 1 - beta * math::cos(x);
			      x_new = x - f / f_prime;
			      if (std::abs(x_new - x) < tolerance)
				{
				  x = x_new;
				  break;
				}
			      x = x_new;
			    }
			  auto theta = x;
			  // now push a photon from thermal bath into the rest frame
			  //  of scattering electron, eqn. 19
			  auto ePrime0 = enBath_ * gamma * (1 - beta * math::cos(theta));
			  // y and x are defined like after eqn.21
			  auto y = 1.0 / ePrime0;
			  // now we check if the collision happens with the KN correction, eqn. 23
			  auto KNcorrection = 0.375 * (F(1, y) - F(1.0 / (1 + 2 / y), y));
			  randNum = Random<real_t>(rand_gen);
			  if (randNum < KNcorrection)
			    {
			      // the collision actually happens
			      randNum = Random<real_t>(rand_gen);
			      // approximate solution from eqn. 27
			      auto x = math::exp(-(1 - randNum) * math::log(1 + 2 / y));
			      auto ePrimeScat = x * ePrime0;
			      // new angle. eqn. 28
			      auto cosPhiScat = y / x - y - 1;
			      // the energy of upscattered photon in lab frame
			      auto eScat = gamma * ePrimeScat * (1 + beta * cosPhiScat);
			      // now we know the energy of the photon and assume it moves
			      // in the direction of upscattering electron/positron
			      
			      // now emit high-energy photon and subtract its momentum
			      // from the momentum of original particle
			      
			      auto gammaNew = gamma + enBath_ - eScat;
			      gammaNew = gammaNew > 1.0 ? gammaNew : 1.0;
			      
			      auto uNew = math::sqrt(gammaNew * gammaNew - 1.0);
			      
			      ux1(p) = uNew * beta_x / beta;
			      ux2(p) = uNew * beta_y / beta;
			      ux3(p) = uNew * beta_z / beta;
									
			      auto phot_p = Kokkos::atomic_fetch_add(&phot_ind(), 1);
			      i1_phot(phot_p + offset_phot) = i1(p);
			      dx1_phot(phot_p + offset_phot) = dx1(p);
			      i2_phot(phot_p + offset_phot) = i2(p);
			      dx2_phot(phot_p + offset_phot) = dx2(p);
			      ux1_phot(phot_p + offset_phot) = eScat * beta_x / beta;
			      ux2_phot(phot_p + offset_phot) = eScat * beta_y / beta;
			      ux3_phot(phot_p + offset_phot) = eScat * beta_z / beta;
			      weight_phot(phot_p + offset_phot) = weight(p);
			      tag_phot(phot_p + offset_phot) = ParticleTag::alive;
			    }
			}
		      random_pool.free_state(rand_gen);
		    }
		});
	      auto phot_ind_h = Kokkos::create_mirror(phot_ind);
	      Kokkos::deep_copy(phot_ind_h, phot_ind);
	      photons.set_npart(offset_phot + phot_ind_h());
	    }
	} // end of IC section
      
      // and this is breit-wheeler section
      if (IsBW)
	{
	  auto &species = domain.species[2];
	  auto ux1 = species.ux1;
	  auto ux2 = species.ux2;
	  auto ux3 = species.ux3;
	  auto i1 = species.i1;
	  auto i2 = species.i2;
	  auto dx1 = species.dx1;
	  auto dx2 = species.dx2;
	  auto weight = species.weight;
	  auto tag = species.tag;
	  
	  array_t<std::size_t> elec_ind("elec_ind");
	  array_t<std::size_t> pos_ind("pos_ind");
	  
	  std::size_t elec_spec;
	  elec_spec = 3;
	  auto &electrons = domain.species[elec_spec];
	  auto offset_elec = electrons.npart();
	  auto ux1_elec = electrons.ux1;
	  auto ux2_elec = electrons.ux2;
	  auto ux3_elec = electrons.ux3;
	  auto i1_elec = electrons.i1;
	  auto i2_elec = electrons.i2;
	  auto dx1_elec = electrons.dx1;
	  auto dx2_elec = electrons.dx2;
	  auto weight_elec = electrons.weight;
	  auto tag_elec = electrons.tag;
	  
	  std::size_t pos_spec;
	  pos_spec = 4;
	  auto &positrons = domain.species[pos_spec];
	  auto offset_pos = positrons.npart();
	  auto ux1_pos = positrons.ux1;
	  auto ux2_pos = positrons.ux2;
	  auto ux3_pos = positrons.ux3;
	  auto i1_pos = positrons.i1;
	  auto i2_pos = positrons.i2;
	  auto dx1_pos = positrons.dx1;
	  auto dx2_pos = positrons.dx2;
	  auto weight_pos = positrons.weight;
	  auto tag_pos = positrons.tag;

	  Kokkos::parallel_for(
	    "BreitWheeler",
	    species.rangeActiveParticles(),
	    Lambda(index_t p) {
	      if (tag(p) == ParticleTag::dead)
		{
		  return;
		}
	      auto px = ux1(p);
	      auto py = ux2(p);
	      auto pz = ux3(p);
	      auto energy = math::sqrt(SQR(px) + SQR(py) + SQR(pz));
	      // following Crinquand+ 2020, we assume cos of angle between the HE photon and
	      // and a random photon from the bath to be uniformly distributed
	      // note the Crinquand+ used definition of s = 0.5*e1*e2*(1-cos Theta), I use more
	      // standard one s = 2*e1*e2*(1-cos Theta)
	      auto rand_gen = random_pool.get_state();
	      auto mu = -1.0 + 2.0 * Random<real_t>(rand_gen);
	      auto s = 2 * energy * enBath_ * (1 - mu);
	      // if not enough energy in COM, exit
	      if (s < 4)
		{
		  random_pool.free_state(rand_gen);
		  return;
		}
	      auto randNum = Random<real_t>(rand_gen);
	      // null collision method, based on thompson cross-section
	      if (randNum < opticalDepthStep)
		{
		  randNum = Random<real_t>(rand_gen);
		  if (randNum < BWfullCS(s, mu) * (1.0 - mu))
		    {
		      // the actual collision happens
		      // now we need to determine the angle at which
		      // electron flies in COM with respect to the initial direction
		      // of gamma-ray (and direction of COM when e1 >> e2)
		      //  see DOI:https://doi.org/10.1103/PhysRevAccelBeams.20.043402
		      auto final_theta = 0.0;
		      real_t theta;
		      bool accepted_angle = false;
		      for (int j = 0; j < 10000; j++)
			{
			  theta = constant::PI * Random<real_t>(rand_gen);
			  randNum = Random<real_t>(rand_gen);
			  if (randNum < dSigma_dO(s, theta))
			    {
			      final_theta = theta;
			      accepted_angle = true;
			      break;
			    }
			}
		      
		      // in case
		      if (!accepted_angle)
			{
			  random_pool.free_state(rand_gen);
			  return;
			}
		      
		      // now we know the direction of electron
		      // and now we follow again Crinquand+ 2020
		      auto gammaPrim = math::sqrt(s) / 2;
		      auto gammaCM = energy / (math::sqrt(s));
		      auto betaCM = math::sqrt(1.0 - s / (energy * energy));
		      auto m1prim = math::cos(final_theta);
		      // Lorentz-factor of the electron in the lab frame
		      auto gammaElec = gammaCM * (gammaPrim + betaCM * m1prim * math::sqrt(s / 4 - 1));
		      // 4-velocity of the electron in the lab frame
		      auto uElec = math::sqrt(gammaElec * gammaElec - 1.0);
		      auto gammaPos = energy + enBath_ - gammaElec;
		      auto uPos = math::sqrt(gammaPos * gammaPos - 1.0);
		      
		      // erase photon
		      tag(p) = ParticleTag::dead;
		      
		      // emit electron-positron pair at the same location
		      auto elec_p = Kokkos::atomic_fetch_add(&elec_ind(), 1);
		      auto pos_p = Kokkos::atomic_fetch_add(&pos_ind(), 1);
		      
		      i1_elec(elec_p + offset_elec) = i1(p);
		      dx1_elec(elec_p + offset_elec) = dx1(p);
		      i2_elec(elec_p + offset_elec) = i2(p);
		      dx2_elec(elec_p + offset_elec) = dx2(p);
		      ux1_elec(elec_p + offset_elec) = uElec * px / energy;
		      ux2_elec(elec_p + offset_elec) = uElec * py / energy;
		      ux3_elec(elec_p + offset_elec) = uElec * pz / energy;
		      weight_elec(elec_p + offset_elec) = weight(p);
		      tag_elec(elec_p + offset_elec) = ParticleTag::alive;
		      if (Kokkos::isnan(uElec * px / energy) || Kokkos::isnan(uElec * py / energy) || Kokkos::isnan(uElec * pz / energy))
			{
			  printf("s=%f, theta=%f, ePh=%f, betaCM=%f, m1prim=%f, gammaElec=%f, uElec=%f \n", s, theta, energy, betaCM, m1prim, gammaElec, uElec);
			}
		      
		      i1_pos(pos_p + offset_pos) = i1(p);
		      dx1_pos(pos_p + offset_pos) = dx1(p);
		      i2_pos(pos_p + offset_pos) = i2(p);
		      dx2_pos(pos_p + offset_pos) = dx2(p);
		      ux1_pos(pos_p + offset_pos) = uPos * px / energy;
		      ux2_pos(pos_p + offset_pos) = uPos * py / energy;
		      ux3_pos(pos_p + offset_pos) = uPos * pz / energy;
		      weight_pos(pos_p + offset_pos) = weight(p);
		      tag_pos(pos_p + offset_pos) = ParticleTag::alive;
		    }
		}
	      random_pool.free_state(rand_gen);
	    });
	  auto elec_ind_h = Kokkos::create_mirror(elec_ind);
	  Kokkos::deep_copy(elec_ind_h, elec_ind);
	  electrons.set_npart(offset_elec + elec_ind_h());
	  
	  auto pos_ind_h = Kokkos::create_mirror(pos_ind);
	  Kokkos::deep_copy(pos_ind_h, pos_ind);
	  positrons.set_npart(offset_pos + pos_ind_h());
	} // this is the end of Breit-Wheeler loop
    }
  };
} // namespace user

#endif
