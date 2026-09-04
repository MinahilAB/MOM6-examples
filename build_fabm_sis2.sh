#!/usr/bin/env bash
# Generate and build a coupled MOM6 + SIS2 + FABM executable with mkmf.
# Required: FABM_ROOT. Optional: MOM6_ROOT, BUILD_DIR, JOBS, FABM_LIBDIR,
# and MK_TEMPLATE. Load site compiler, MPI and NetCDF modules first.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mom6_root=${MOM6_ROOT:-"${repo_root}/../MOM6"}
build_dir=${BUILD_DIR:-"${repo_root}/build_fabm_sis2"}
jobs=${JOBS:-8}
mk_template=${MK_TEMPLATE:-"${repo_root}/src/mkmf/templates/hpcme-intel21.mk"}
mkmf="${repo_root}/src/mkmf/bin/mkmf"

if [[ -z ${FABM_ROOT:-} ]]; then echo "ERROR: set FABM_ROOT." >&2; exit 2; fi
if [[ ! -f "${FABM_ROOT}/include/fabm.mod" ]]; then
  echo "ERROR: missing ${FABM_ROOT}/include/fabm.mod." >&2; exit 2
fi
if [[ ! -x "${mkmf}" || ! -d "${mom6_root}/src" ]]; then
  echo "ERROR: mkmf or MOM6_ROOT source checkout not found." >&2; exit 2
fi
if [[ -n ${FABM_LIBDIR:-} ]]; then fabm_libdir=${FABM_LIBDIR}
elif [[ -e "${FABM_ROOT}/lib64/libfabm.a" || -e "${FABM_ROOT}/lib64/libfabm.so" ]]; then fabm_libdir="${FABM_ROOT}/lib64"
elif [[ -e "${FABM_ROOT}/lib/libfabm.a" || -e "${FABM_ROOT}/lib/libfabm.so" ]]; then fabm_libdir="${FABM_ROOT}/lib"
else echo "ERROR: libfabm not found under FABM_ROOT." >&2; exit 2; fi

# BFM/OGS installs libadj beside libfabm. It must follow libfabm when
# linking static archives; ordinary FABM installations keep -lfabm alone.
fabm_extra_libs=""
if [[ -e "${fabm_libdir}/libadj.a" || -e "${fabm_libdir}/libadj.so" ]]; then
  fabm_extra_libs=" -ladj"
fi

fms_build="${build_dir}/fms"
mom_build="${build_dir}/mom"
mkdir -p "${fms_build}" "${mom_build}"
printf "MOM6 source: %s\nFABM prefix: %s\nBuild directory: %s\n" "${mom6_root}" "${FABM_ROOT}" "${build_dir}"

# These pinned manifests describe the tested MOM6/SIS2/FMS source layout.
cp "${repo_root}/config/fabm_sis2/fms_path_names" "${fms_build}/path_names"
perl -pe "s!\Q../../../MOM6\E!${mom6_root}!g" \
  "${repo_root}/config/fabm_sis2/mom_sis2_path_names" > "${mom_build}/path_names"

(
  cd "${fms_build}"
  "${mkmf}" -t "${mk_template}" -p libfms.a \
    -c "-Duse_libMPI -Duse_netCDF -DSPMD" path_names
  make -j "${jobs}" NETCDF=3 libfms.a
)
(
  cd "${mom_build}"
  "${mkmf}" -t "${mk_template}" -p MOM6 \
    -o "-I../fms -I${FABM_ROOT}/include" \
    -l "-L../fms -lfms -L${fabm_libdir} -lfabm${fabm_extra_libs}" \
    -c "-Duse_libMPI -Duse_netCDF -DSPMD -D_FABM_ -DUSE_LOG_DIAG_FIELD_INFO -Duse_AM3_physics -D_USE_LEGACY_LAND_" \
    path_names
  make -j "${jobs}" NETCDF=3 MOM6
)
ln -sfn mom/MOM6 "${build_dir}/MOM6"
echo "Built coupled executable: ${build_dir}/MOM6"
