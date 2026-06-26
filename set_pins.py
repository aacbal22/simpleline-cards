# -*- coding: utf-8 -*-
"""
기존 전 직원의 '사진 변경 본인확인 PIN'(휴대폰 뒷 4자리)을 KV에 일괄 등록/동기화.
명함에서 사진을 탭해 뒷 4자리로 바꾸려면 각 직원의 PIN 이 KV에 있어야 한다.

사용법:  python set_pins.py
"""
import os, sys, glob, json
import make_token as mt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))

for jp in sorted(glob.glob(os.path.join(ROOT, "cards", "*.json"))):
    with open(jp, encoding="utf-8") as f:
        d = json.load(f)
    slug = d["slug"]
    phone = d["front"]["phones"][0]
    pin = mt.set_pin(slug, phone)
    print(f"  {d['front']['name']}({slug}) → PIN {pin}")

print("\n[완료] 전 직원 PIN 등록됨. 명함에서 사진 탭 → 휴대폰 뒷4자리로 변경 가능.")
