#ifndef PROBLEM_GENERATOR_H
#define PROBLEM_GENERATOR_H

#include "enums.h"
#include "global.h"

#include "arch/kokkos_aliases.h"
#include "arch/traits.h"
#include "utils/error.h"
#include "utils/numeric.h"

#include "archetypes/energy_dist.h"
#include "archetypes/problem_generator.h"
#include "archetypes/utils.h"
#include "framework/domain/domain.h"
#include "framework/domain/metadomain.h"
#include "kernels/injectors.hpp"

#include <cmath>

namespace user {
  using namespace ntt;
  using prmvec_t = std::vector<real_t>;

  template <Dimension D>
  struct InitFields {

    /*
      Sets up background magnetic field for the simulation.

      @param bmag: magnetic field scaling
      @param btheta: magnetic field polar angle
      @param bphi: magnetic field azimuthal angle
    */
    InitFields(real_t bmag, real_t btheta, real_t bphi)
      : Bmag { bmag }
      , Btheta { btheta * static_cast<real_t>(convert::deg2rad) }
      , Bphi { bphi * static_cast<real_t>(convert::deg2rad) } {}

    // magnetic field components
    Inline auto bx1(const coord_t<D>&) const -> real_t {
      return Bmag * math::cos(Btheta);
    }

    Inline auto bx2(const coord_t<D>&) const -> real_t {
      return Bmag * math::sin(Btheta) * math::sin(Bphi);
    }

    Inline auto bx3(const coord_t<D>&) const -> real_t {
      return Bmag * math::sin(Btheta) * math::cos(Bphi);
    }

  private:
    const real_t Btheta, Bphi, Bmag;
  };

  /*
    Quiet start: same as arch::UniformInjector_kernel (random Maxwellian velocities,
    both species of a pair at the same position) except that positions are evenly
    spaced inside every cell, x = i + (j + 1/2)/npc, instead of uniformly random.
  */
  template <SimEngine::type S, class M, class ED1, class ED2>
  struct QuietInjector1D_kernel {
    array_t<int*>      i1s_1, i2s_1, i3s_1;
    array_t<prtldx_t*> dx1s_1, dx2s_1, dx3s_1;
    array_t<real_t*>   ux1s_1, ux2s_1, ux3s_1;
    array_t<real_t*>   phis_1, weights_1;
    array_t<short*>    tags_1;
    array_t<npart_t**> pldis_1;

    array_t<int*>      i1s_2, i2s_2, i3s_2;
    array_t<prtldx_t*> dx1s_2, dx2s_2, dx3s_2;
    array_t<real_t*>   ux1s_2, ux2s_2, ux3s_2;
    array_t<real_t*>   phis_2, weights_2;
    array_t<short*>    tags_2;
    array_t<npart_t**> pldis_2;

    const npart_t offset1, offset2, npc;
    const M       metric;
    const ED1     energy_dist_1;
    const ED2     energy_dist_2;

    QuietInjector1D_kernel(Particles<M::Dim, M::CoordType>& sp1,
                           Particles<M::Dim, M::CoordType>& sp2,
                           npart_t                          npc,
                           const M&                         metric,
                           const ED1&                       ed1,
                           const ED2&                       ed2)
      : i1s_1 { sp1.i1 }, i2s_1 { sp1.i2 }, i3s_1 { sp1.i3 }
      , dx1s_1 { sp1.dx1 }, dx2s_1 { sp1.dx2 }, dx3s_1 { sp1.dx3 }
      , ux1s_1 { sp1.ux1 }, ux2s_1 { sp1.ux2 }, ux3s_1 { sp1.ux3 }
      , phis_1 { sp1.phi }, weights_1 { sp1.weight }, tags_1 { sp1.tag }, pldis_1 { sp1.pld_i }
      , i1s_2 { sp2.i1 }, i2s_2 { sp2.i2 }, i3s_2 { sp2.i3 }
      , dx1s_2 { sp2.dx1 }, dx2s_2 { sp2.dx2 }, dx3s_2 { sp2.dx3 }
      , ux1s_2 { sp2.ux1 }, ux2s_2 { sp2.ux2 }, ux3s_2 { sp2.ux3 }
      , phis_2 { sp2.phi }, weights_2 { sp2.weight }, tags_2 { sp2.tag }, pldis_2 { sp2.pld_i }
      , offset1 { sp1.npart() }
      , offset2 { sp2.npart() }
      , npc { npc }
      , metric { metric }
      , energy_dist_1 { ed1 }
      , energy_dist_2 { ed2 } {}

    Inline void operator()(index_t p) const {
      tuple_t<int, Dim::_1D>      xi_Cd { static_cast<int>(p / npc) };
      tuple_t<prtldx_t, Dim::_1D> dxi_Cd { static_cast<prtldx_t>(
        (static_cast<real_t>(p % npc) + HALF) / static_cast<real_t>(npc)) };
      coord_t<Dim::_1D> x_Cd { static_cast<real_t>(xi_Cd[0]) + static_cast<real_t>(dxi_Cd[0]) };
      coord_t<Dim::_1D> x_Ph { ZERO };
      metric.template convert<Crd::Cd, Crd::Ph>(x_Cd, x_Ph);
      vec_t<Dim::_3D> v1 { ZERO }, v2 { ZERO };
      energy_dist_1(x_Ph, v1);
      energy_dist_2(x_Ph, v2);
      // clang-format off
      kernel::InjectParticle<Dim::_1D, M::CoordType, false>(
        p + offset1, i1s_1, i2s_1, i3s_1, dx1s_1, dx2s_1, dx3s_1,
        ux1s_1, ux2s_1, ux3s_1, phis_1, weights_1, tags_1, pldis_1,
        xi_Cd, dxi_Cd, v1, ONE, ZERO);
      kernel::InjectParticle<Dim::_1D, M::CoordType, false>(
        p + offset2, i1s_2, i2s_2, i3s_2, dx1s_2, dx2s_2, dx3s_2,
        ux1s_2, ux2s_2, ux3s_2, phis_2, weights_2, tags_2, pldis_2,
        xi_Cd, dxi_Cd, v2, ONE, ZERO);
      // clang-format on
    }
  };

  template <SimEngine::type S, class M>
  struct PGen : public arch::ProblemGenerator<S, M> {

    // compatibility traits for the problem generator
    static constexpr auto engines = traits::compatible_with<SimEngine::SRPIC>::value;
    static constexpr auto metrics = traits::compatible_with<Metric::Minkowski>::value;
    static constexpr auto dimensions = traits::compatible_with<Dim::_1D>::value;

    // for easy access to variables in the child class
    using arch::ProblemGenerator<S, M>::D;
    using arch::ProblemGenerator<S, M>::C;
    using arch::ProblemGenerator<S, M>::params;

    prmvec_t drifts_in_x, drifts_in_y, drifts_in_z;
    prmvec_t densities, temperatures;
    // initial magnetic field
    real_t        Btheta, Bphi, Bmag;
    InitFields<D> init_flds;

    inline PGen(const SimulationParams& p, const Metadomain<S, M>& global_domain)
      : arch::ProblemGenerator<S, M> { p }
      , drifts_in_x { p.template get<prmvec_t>("setup.drifts_in_x", prmvec_t {}) }
      , drifts_in_y { p.template get<prmvec_t>("setup.drifts_in_y", prmvec_t {}) }
      , drifts_in_z { p.template get<prmvec_t>("setup.drifts_in_z", prmvec_t {}) }
      , Bmag { p.template get<real_t>("setup.Bmag", ZERO) }
      , Btheta { p.template get<real_t>("setup.Btheta", ZERO) }
      , Bphi { p.template get<real_t>("setup.Bphi", ZERO) }
      , init_flds { Bmag, Btheta, Bphi }
      , densities { p.template get<prmvec_t>("setup.densities", prmvec_t {}) }
      , temperatures { p.template get<prmvec_t>("setup.temperatures", prmvec_t {}) } {
      const auto nspec = p.template get<std::size_t>("particles.nspec");
      raise::ErrorIf(nspec % 2 != 0,
                     "Number of species must be even for this setup",
                     HERE);
      for (auto n = 0u; n < nspec; n += 2) {
        raise::ErrorIf(
          global_domain.species_params()[n].charge() !=
            -global_domain.species_params()[n + 1].charge(),
          "Charges of i-th and i+1-th species must be opposite for this setup",
          HERE);
      }
      for (auto* specs :
           { &drifts_in_x, &drifts_in_y, &drifts_in_z, &temperatures }) {
        if (specs->empty()) {
          for (auto n = 0u; n < nspec; ++n) {
            specs->push_back(ZERO);
          }
        }
        raise::ErrorIf(specs->size() != nspec,
                       "Drift vector and/or temperature vector length does "
                       "not match number of species",
                       HERE);
      }
      if (densities.empty()) {
        for (auto n = 0u; n < nspec; n += 2) {
          densities.push_back(TWO / static_cast<real_t>(nspec));
        }
      }
      raise::ErrorIf(densities.size() != nspec / 2,
                     "Density vector length must be half of the number of "
                     "species (per each pair of species)",
                     HERE);
    }

    inline void InitPrtls(Domain<S, M>& domain) {
      raise::ErrorIf(params.template get<bool>("particles.use_weights"),
                     "Quiet start assumes Cartesian, unweighted particles",
                     HERE);
      const auto nspec = domain.species.size();
      const auto ppc0  = params.template get<real_t>("particles.ppc0");
      const auto ncell = static_cast<npart_t>(domain.mesh.n_active(in::x1));
      for (auto n = 0u; n < nspec; n += 2) {
        // same particles-per-cell-per-species as arch::ComputeNumInject
        const auto npc_r = static_cast<double>(ppc0) * densities[n / 2] * 0.5;
        const auto npc   = static_cast<npart_t>(std::lround(npc_r));
        raise::ErrorIf(npc < 1 or std::abs(npc_r - static_cast<double>(npc)) > 1e-6,
                       "Quiet start needs an integer number of particles per cell "
                       "per species: ppc0 * densities[i] / 2",
                       HERE);
        raise::ErrorIf(domain.species[n].use_tracking() or
                         domain.species[n + 1].use_tracking(),
                       "Quiet start does not support particle tracking",
                       HERE);
        // same Maxwellians (temperature / mass, drift 4-velocity) as
        // arch::InjectUniformMaxwellians
        const auto maxwellian_1 = arch::Maxwellian<S, M>(
          domain.mesh.metric,
          domain.random_pool(),
          temperatures[n] / domain.species[n].mass(),
          prmvec_t { drifts_in_x[n], drifts_in_y[n], drifts_in_z[n] });
        const auto maxwellian_2 = arch::Maxwellian<S, M>(
          domain.mesh.metric,
          domain.random_pool(),
          temperatures[n + 1] / domain.species[n + 1].mass(),
          prmvec_t { drifts_in_x[n + 1], drifts_in_y[n + 1], drifts_in_z[n + 1] });
        const auto nparticles = npc * ncell;
        Kokkos::parallel_for(
          "QuietInject",
          nparticles,
          QuietInjector1D_kernel<S, M, decltype(maxwellian_1), decltype(maxwellian_2)>(
            domain.species[n],
            domain.species[n + 1],
            npc,
            domain.mesh.metric,
            maxwellian_1,
            maxwellian_2));
        domain.species[n].set_npart(domain.species[n].npart() + nparticles);
        domain.species[n + 1].set_npart(domain.species[n + 1].npart() + nparticles);
      }
    }
  };

} // namespace user

#endif
