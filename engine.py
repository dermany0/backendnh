import requests
import json

class OSINTEngine:
    SEARCH_URL = "https://api.hazaclub.com/search/user"
    DETAIL_URL = "https://api.hazaclub.com/user/block"

    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": "Dart/3.8 (dart:io)"
    }

    H_COMMON = {
        "h_mid": 101846893,
        "h_token": "UqXfaQAAAABtDxIGAAAAAD+OncBQZI42AA==",
        "h_app": 0,
        "h_av": "3.7.0",
        "h_dt": 1,
        "h_android_id": "951aa291e2d38e4a",
        "h_adid": "d03a782e-8065-4a5d-a628-0ba703276b43",
        "h_ch": "GooglePlay",
        "h_nt": 1,
        "h_lang": "tr",
        "h_os": "28"
    }

    def search_user(self, keyword):
        payload = {"keyword": str(keyword), "scene": "all", **self.H_COMMON}
        r = requests.post(self.SEARCH_URL, json=payload, headers=self.HEADERS, timeout=15)
        try:
            data = r.json()
        except:
            return []
        if data.get("ret") != 1:
            return []
        return data.get("data", {}).get("list", [])

    def get_user(self, mid):
        """
        TRICK: /user/block endpoint'i zaten engellenmiş kullanıcı için
        data döndürmüyor. Bu yüzden önce UNBLOCK (is_cancel=True)
        yapıp state'i sıfırlıyoruz, sonra BLOCK (is_cancel=False)
        ile taze veriyi çekiyoruz.
        """

        # 🔓 STEP 1: Önce UNBLOCK — engeli kaldır (state reset)
        unblock_payload = {"to_mid": mid, "is_cancel": True, **self.H_COMMON}
        try:
            requests.post(self.DETAIL_URL, json=unblock_payload, headers=self.HEADERS, timeout=10)
            print(f"[OSINT] Step 1: Unblock sent for MID {mid}")
        except:
            pass

        # 🔒 STEP 2: Tekrar BLOCK — taze data al
        block_payload = {"to_mid": mid, "is_cancel": False, **self.H_COMMON}
        r = requests.post(self.DETAIL_URL, json=block_payload, headers=self.HEADERS, timeout=15)

        try:
            data = r.json()
        except:
            print(f"❌ JSON parse fail for MID {mid}")
            return None

        print(f"[DEBUG] Block response keys: {list(data.keys())}, ret: {data.get('ret')}")

        if data.get("ret") != 1:
            return None

        # 🔥 MULTI-FALLBACK PARSER
        member = None
        if isinstance(data, dict):
            member = (
                data.get("data", {}).get("to_member")
                or data.get("to_member")
                or (data.get("data") if isinstance(data.get("data"), dict) else None)
            )

        if not member:
            print(f"⚠️ member still None for MID {mid} (data keys: {list(data.keys())})")
            return None

        u = member
        g = u.get("google_user") or {}

        result = {
            "nick": g.get("nick") if u.get("google_user") else u.get("nick"),
            "app_nick": u.get("nick"),
            "google_nick": g.get("nick"),
            "open_id": g.get("open_id") if u.get("google_user") else None,
            "avatar": u.get("avatar"),
            "google_avatar": g.get("avatar") if u.get("google_user") else None,
            "email": g.get("email") if u.get("google_user") else None,
            "login_device": u.get("login_device"),
            "last_login_time": u.get("last_login_time"),
            "first_login": u.get("first_login_info") or {},
            "is_online": u.get("is_online", False),
            "vip_level": u.get("vip_level", 0),
        }
        print(f"[OSINT] ✅ Got detail: {result.get('app_nick')} / {result.get('email')} / IP: {(result.get('first_login') or {}).get('ip')}")
        return result

    # ─── ANA ARAMA ───
    def search(self, query: str):
        try:
            results = self.search_user(query)
            print(f"[OSINT] Search: {query} -> {len(results)} users found.")

            if not results:
                return {"success": True, "results": [], "type": "keyword", "count": 0}

            final_results = []
            for item in results[:3]:
                mid = item.get("mid")
                pretty_id = item.get("pretty_number")

                detail = self.get_user(mid)

                if detail:
                    first = detail.get("first_login") or {}
                    mapped = {
                        "id": str(mid),
                        "mid": str(mid),
                        "pretty_id": str(pretty_id or "—"),
                        "nickname": detail.get("app_nick") or detail.get("nick") or item.get("nick") or "Unknown",
                        "google_nickname": detail.get("google_nick") or "—",
                        "email": detail.get("email") or "—",
                        "open_id": detail.get("open_id") or "—",
                        "avatar_url": item.get("avatar") or detail.get("avatar"),
                        "google_avatar_url": detail.get("google_avatar"),
                        "last_login_time": detail.get("last_login_time") or "—",
                        "login_device": detail.get("login_device") or "—",
                        "first_login_ip": first.get("ip") or "—",
                        "is_online": detail.get("is_online", False),
                        "vip_level": detail.get("vip_level", 0),
                    }
                else:
                    mapped = {
                        "id": str(mid),
                        "mid": str(mid),
                        "pretty_id": str(pretty_id or "—"),
                        "nickname": item.get("nick") or "Unknown",
                        "google_nickname": "—",
                        "email": "—",
                        "open_id": "—",
                        "avatar_url": item.get("avatar"),
                        "google_avatar_url": None,
                        "last_login_time": "—",
                        "login_device": "—",
                        "first_login_ip": "—",
                        "is_online": False,
                        "vip_level": 0,
                    }

                final_results.append(mapped)

            return {"success": True, "results": final_results, "type": "keyword", "count": len(final_results)}

        except Exception as e:
            print(f"[CRITICAL] {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "type": "keyword"}
