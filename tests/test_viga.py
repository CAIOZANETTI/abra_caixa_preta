import pytest
from app import calcular_viga

TOL = 1e-6


@pytest.mark.parametrize("L,q,RA,Vmax,Mmax", [
    (4.0,  5.0,  10.0,  10.0,  10.0),
    (6.0,  20.0, 60.0,  60.0,  90.0),
    (10.0, 50.0, 250.0, 250.0, 625.0),
])
def test_viga(L, q, RA, Vmax, Mmax):
    r = calcular_viga(L, q)
    assert abs(r["RA_kN"]     - RA)   < TOL
    assert abs(r["RB_kN"]     - RA)   < TOL
    assert abs(r["Vmax_kN"]   - Vmax) < TOL
    assert abs(r["Mmax_kN_m"] - Mmax) < TOL
