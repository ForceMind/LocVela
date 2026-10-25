"""Adapter wiring tested against explicit stubs; actual upstream imports checked separately in CI."""
import plistlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from adapters.ios_pymobiledevice3.backend import Pmd3Backend
from adapters.ios_pymobiledevice3.protocol import Fault

class BackendContract(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events=[]
        parent=self
        class Rsd:
            def __init__(self,address):
                self.address=address; self.udid="TEST-DEVICE-0000"; self.product_version="18.4.1"; self.developer=True
            async def connect(self): parent.events.append("rsd_connect")
            async def close(self): parent.events.append("rsd_close")
            async def get_developer_mode_status(self): return self.developer
        self.rsd=Rsd(("127.0.0.1",1))
        class Tunnel:
            def __init__(self,serial,autopair):
                parent.events.append(("tunnel",serial,autopair))
            async def aopen(self): return parent.rsd
            async def aclose(self): parent.events.append("tunnel_close")
        class Dvt:
            def __init__(self,rsd): parent.events.append("dvt_construct")
            async def __aenter__(self): return self
            async def __aexit__(self,*args): parent.events.append("dvt_close")
        class Simulation:
            def __init__(self,dvt): pass
            async def __aenter__(self): return self
            async def __aexit__(self,*args): parent.events.append("channel_close")
            async def set(self,latitude,longitude): parent.events.append(("set",latitude,longitude))
            async def clear(self): parent.events.append("clear_sent_no_reply")
        modules={
            "pymobiledevice3.remote.remote_service_discovery": {"RemoteServiceDiscoveryService":lambda address:parent.rsd},
            "pymobiledevice3.remote.userspace_tunnel": {"UserspaceRsdTunnel":Tunnel},
            "pymobiledevice3.services.dvt.instruments.dvt_provider": {"DvtProvider":Dvt},
            "pymobiledevice3.services.dvt.instruments.location_simulation": {"LocationSimulation":Simulation},
        }
        self.modules={}
        for name,attrs in modules.items():
            module=types.ModuleType(name); module.__dict__.update(attrs); self.modules[name]=module
        self.patch_modules=patch.dict(sys.modules,self.modules); self.patch_modules.start()
        self.patch_version=patch("adapters.ios_pymobiledevice3.backend.dependency_check"); self.patch_version.start()
    def tearDown(self): self.patch_version.stop(); self.patch_modules.stop()
    async def test_exact_device_no_autopair_no_reopen_per_fix(self):
        p=Pmd3Backend(None,"TEST-DEVICE-0000"); await p.connect()
        await p.set(1,2); await p.set(3,4); await p.clear(); await p.close()
        self.assertEqual(self.events[0],("tunnel","TEST-DEVICE-0000",False))
        self.assertEqual(self.events.count("dvt_construct"),1)
        self.assertEqual(self.events[-3:],["channel_close","dvt_close","tunnel_close"])
        self.assertFalse(p.clear_has_reply)
    async def test_wrong_device_before_developer_service(self):
        p=Pmd3Backend(None,"ANOTHER-DEVICE")
        with self.assertRaises(Fault) as c: await p.connect()
        self.assertEqual(c.exception.code,"wrong_device"); self.assertNotIn("dvt_construct",self.events)
        await p.close(); self.assertIn("tunnel_close",self.events)
    async def test_wrong_ios_before_developer_service(self):
        self.rsd.product_version="18.5"
        p=Pmd3Backend(None,"TEST-DEVICE-0000")
        with self.assertRaises(Fault) as c: await p.connect()
        self.assertEqual(c.exception.code,"unexpected_ios_version"); await p.close()
    async def test_developer_mode_required(self):
        self.rsd.developer=False; p=Pmd3Backend(None,"TEST-DEVICE-0000")
        with self.assertRaises(Fault) as c: await p.connect()
        self.assertEqual(c.exception.code,"developer_mode_required"); await p.close()
    async def test_rsd_mode_not_a_new_tunnel(self):
        p=Pmd3Backend(("127.0.0.1",1),"TEST-DEVICE-0000"); await p.connect(); await p.close()
        self.assertEqual(self.events[0],"rsd_connect"); self.assertEqual(self.events[-1],"rsd_close")
        self.assertFalse(any(type(e) is tuple and e[0]=="tunnel" for e in self.events))
    async def test_closed_adapter_cannot_send(self):
        p=Pmd3Backend(None,"TEST-DEVICE-0000"); await p.connect(); await p.close()
        with self.assertRaises(Fault): await p.set(1,2)
    async def test_duplicate_connect_rejected(self):
        p=Pmd3Backend(None,"TEST-DEVICE-0000"); await p.connect()
        with self.assertRaises(Fault): await p.connect()
        await p.close()

class ProbeContract(unittest.TestCase):
    def test_foreground_only_and_no_tracking(self):
        root=Path(__file__).resolve().parents[1]/"probes/ios/LocVelaProbe"
        info=plistlib.loads((root/"Info.plist").read_bytes())
        self.assertIn("NSLocationWhenInUseUsageDescription",info)
        self.assertNotIn("UIBackgroundModes",info)
        self.assertNotIn("NSLocationAlwaysAndWhenInUseUsageDescription",info)
        privacy=plistlib.loads((root/"PrivacyInfo.xcprivacy").read_bytes())
        self.assertFalse(privacy["NSPrivacyTracking"])
        self.assertEqual(privacy["NSPrivacyCollectedDataTypes"],[])

    def test_swift_six_concurrency_gate(self):
        root=Path(__file__).resolve().parents[1]/"probes/ios"
        project=(root/"LocVelaProbe.xcodeproj/project.pbxproj").read_text()
        self.assertEqual(project.count("SWIFT_VERSION = 6.0;"), 2)
        self.assertEqual(project.count("SWIFT_TREAT_WARNINGS_AS_ERRORS = YES;"), 2)
        source=(root/"LocVelaProbe/LocationObserver.swift").read_text()
        self.assertEqual(source.count("nonisolated func locationManager"), 3)
        self.assertEqual(source.count("MainActor.assumeIsolated"), 3)
        self.assertNotIn("@unchecked", source)
        info=plistlib.loads((root/"LocVelaProbe/Info.plist").read_bytes())
        self.assertEqual(len(info["UISupportedInterfaceOrientations~ipad"]), 4)

if __name__ == "__main__": unittest.main()
