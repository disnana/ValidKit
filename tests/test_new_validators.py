import unittest
import datetime
import uuid
import ipaddress
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from validkit import v, validate, ValidationError

class TestNewValidators(unittest.TestCase):
    def test_datetime(self):
        # 正常系 (datetime)
        now = datetime.datetime.now()
        schema = {"dt": v.datetime().after(now - datetime.timedelta(days=1))}
        data = {"dt": now}
        self.assertEqual(validate(data, schema)["dt"], now)

        # 正常系 (date -> datetime 変換)
        today = datetime.date.today()
        schema = {"dt": v.datetime()}
        data = {"dt": today}
        self.assertEqual(validate(data, schema)["dt"], today)

        # 異常系 (期限切れ)
        past = now - datetime.timedelta(days=10)
        schema = {"dt": v.datetime().after(now)}
        with self.assertRaises(ValidationError):
            validate({"dt": past}, schema)

        # coerce
        schema = {"dt": v.datetime().coerce()}
        iso_str = "2026-12-31T23:59:59"
        result = validate({"dt": iso_str}, schema)
        self.assertIsInstance(result["dt"], datetime.datetime)
        self.assertEqual(result["dt"].year, 2026)

    def test_datetime_timezone(self):
        # Timezone aware input vs Naive criteria
        aware_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        schema = {"dt": v.datetime().after_now()}
        # This shouldn't raise TypeError
        self.assertEqual(validate({"dt": aware_dt}, schema)["dt"], aware_dt)

        # Naive input vs Aware criteria
        naive_dt = datetime.datetime.now() + datetime.timedelta(days=2)
        aware_limit = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        schema = {"dt": v.datetime().after(aware_limit)}
        # This shouldn't raise TypeError
        self.assertEqual(validate({"dt": naive_dt}, schema)["dt"], naive_dt)

    def test_uuid(self):
        u_str = "550e8400-e29b-41d4-a716-446655440000"
        u_obj = uuid.UUID(u_str)

        # 正常系 (文字列)
        self.assertEqual(validate({"id": u_str}, {"id": v.uuid()})["id"], u_str)
        # 正常系 (オブジェクト)
        self.assertEqual(validate({"id": u_obj}, {"id": v.uuid()})["id"], u_obj)

        # version 指定
        v4_str = str(uuid.uuid4())
        self.assertEqual(validate({"id": v4_str}, {"id": v.uuid().version(4)})["id"], v4_str)
        with self.assertRaises(ValidationError):
            validate({"id": "invalid-uuid"}, {"id": v.uuid()})

    def test_mac(self):
        mac = "00:11:22:33:44:55"
        self.assertEqual(validate({"mac": mac}, {"mac": v.mac()})["mac"], mac)
        
        with self.assertRaises(ValidationError):
            validate({"mac": "invalid-mac"}, {"mac": v.mac()})

    def test_sid(self):
        sid = "S-1-5-21-3623811015-3361044348-30300820-1013"
        self.assertEqual(validate({"sid": sid}, {"sid": v.sid()})["sid"], sid)
        
        with self.assertRaises(ValidationError):
            validate({"sid": "invalid-sid"}, {"sid": v.sid()})

    def test_hwid(self):
        # 正常系
        hwid = "ABCDEF123456"
        self.assertEqual(validate({"h": hwid}, {"h": v.hwid().length(12)})["h"], hwid)
        
        # hex
        self.assertEqual(validate({"h": "deadbeef"}, {"h": v.hwid().hex()})["h"], "deadbeef")
        
        with self.assertRaises(ValidationError):
            validate({"h": "not-hex!"}, {"h": v.hwid().hex()})

    def test_ip(self):
        ipv4 = "192.168.1.1"
        self.assertEqual(validate({"ip": ipv4}, {"ip": v.ip()})["ip"], ipv4)
        
        # v4_only
        self.assertEqual(validate({"ip": ipv4}, {"ip": v.ip().v4_only()})["ip"], ipv4)
        
        # coerce
        res = validate({"ip": ipv4}, {"ip": v.ip().coerce()})
        self.assertIsInstance(res["ip"], ipaddress.IPv4Address)

        with self.assertRaises(ValidationError):
            validate({"ip": "2001:db8::1"}, {"ip": v.ip().v4_only()})

    def test_snowflake(self):
        sf_str = "123456789012345678"
        sf_int = 123456789012345678
        self.assertEqual(validate({"s": sf_str}, {"s": v.snowflake()})["s"], sf_str)
        self.assertEqual(validate({"s": sf_int}, {"s": v.snowflake()})["s"], sf_int)

        # coerce
        res = validate({"s": sf_str}, {"s": v.snowflake().coerce()})
        self.assertEqual(res["s"], sf_int)

        with self.assertRaises(ValidationError):
            validate({"s": "not-a-number"}, {"s": v.snowflake()})

    def test_version(self):
        ver = "1.2.3-alpha.1+build.10"
        self.assertEqual(validate({"v": ver}, {"v": v.version()})["v"], ver)
        
        with self.assertRaises(ValidationError):
            validate({"v": "1.2"}, {"v": v.version()}) # SemVer must be x.y.z

if __name__ == "__main__":
    unittest.main()
