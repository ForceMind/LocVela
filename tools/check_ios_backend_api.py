"""No-device API contract test against the exact installed upstream dependency."""
import inspect
from adapters.ios_pymobiledevice3.backend import dependency_check

def main():
    dependency_check()
    from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService as RSD
    from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation, LocationSimulationService
    assert {"serial", "autopair"} <= set(inspect.signature(UserspaceRsdTunnel).parameters)
    assert inspect.iscoroutinefunction(UserspaceRsdTunnel.aopen)
    assert inspect.iscoroutinefunction(UserspaceRsdTunnel.aclose)
    for cls in (RSD, DvtProvider, LocationSimulation):
        assert callable(getattr(cls, "__aenter__"))
        assert callable(getattr(cls, "__aexit__"))
    for cls, name in ((RSD, "connect"), (RSD, "close"), (RSD, "get_developer_mode_status"),
                      (LocationSimulation, "set"), (LocationSimulation, "clear")):
        assert inspect.iscoroutinefunction(getattr(cls, name)), (cls.__name__, name)
    assert list(inspect.signature(LocationSimulation.set).parameters) == ["self", "latitude", "longitude"]
    assert "expects_reply=False" in inspect.getsource(LocationSimulationService)
    # No connect or location call is executed here.
    print("Pinned pymobiledevice3 Python API import/signature check passed. NO DEVICE TEST.")

if __name__ == "__main__":
    main()
