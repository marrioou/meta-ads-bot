import requests
import re
import time
import schedule
from datetime import datetime

# ===================== الإعدادات =====================
META_ACCESS_TOKEN = "YOUR_META_ACCESS_TOKEN_HERE"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID_HERE"
BALANCE_THRESHOLD  = 1000   # جنيه — حد التحذير
CHECK_INTERVAL_HRS = 3      # كل كام ساعة يشتغل
# ======================================================

META_API = "https://graph.facebook.com/v20.0"


def get_ad_accounts():
    url = f"{META_API}/me/adaccounts"
    params = {
        "fields": "name,account_id,funding_source_details",
        "access_token": META_ACCESS_TOKEN,
        "limit": 100
    }
    accounts = []
    while url:
        r = requests.get(url, params=params)
        data = r.json()
        if "error" in data:
            raise Exception(f"Meta API Error: {data['error']['message']}")
        accounts.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}
    return accounts


def extract_balance(funding_source_details):
    if not funding_source_details:
        return None
    display = funding_source_details.get("display_string", "")
    match = re.search(r"[\d,]+\.?\d*", display.replace(",", ""))
    if match:
        return float(match.group())
    return None


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    r = requests.post(url, json=payload)
    return r.ok


def check_and_notify():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] جاري فحص الحسابات...")

    try:
        accounts = get_ad_accounts()
    except Exception as e:
        send_telegram(f"⚠️ خطأ في الاتصال بـ Meta API:\n{e}")
        return

    low_accounts = []
    report_lines = [f"📊 <b>تقرير أرصدة Meta Ads</b>\n🕐 {now}\n"]

    for acc in accounts:
        name    = acc.get("name", "بدون اسم")
        balance = extract_balance(acc.get("funding_source_details"))

        if balance is None:
            line = f"• {name} — رصيد غير متاح"
        elif balance < BALANCE_THRESHOLD:
            line = f"🔴 {name} — <b>{balance:,.0f} ج</b> ← يحتاج شحن!"
            low_accounts.append((name, balance))
        elif balance < BALANCE_THRESHOLD * 2.5:
            line = f"🟡 {name} — {balance:,.0f} ج"
        else:
            line = f"🟢 {name} — {balance:,.0f} ج"

        report_lines.append(line)

    # ملخص في الأسفل
    report_lines.append(f"\n<b>إجمالي الحسابات:</b> {len(accounts)}")
    if low_accounts:
        report_lines.append(f"🚨 <b>تحتاج شحن عاجل:</b> {len(low_accounts)} حساب")

    send_telegram("\n".join(report_lines))

    # إنذار منفصل للحسابات الحرجة
    if low_accounts:
        alert_lines = ["🚨 <b>تنبيه عاجل — حسابات تحتاج شحن!</b>\n"]
        for name, bal in low_accounts:
            alert_lines.append(f"• {name}: <b>{bal:,.0f} ج</b>")
        alert_lines.append("\n👆 يرجى إبلاغ العملاء بالشحن فوراً")
        send_telegram("\n".join(alert_lines))

    print(f"[{now}] تم الإرسال. حسابات تحتاج شحن: {len(low_accounts)}")


def main():
    print("✅ البوت شغال!")
    print(f"   سيفحص الحسابات كل {CHECK_INTERVAL_HRS} ساعات")
    print(f"   حد التحذير: {BALANCE_THRESHOLD} ج\n")

    # شغّل فوراً عند البدء
    check_and_notify()

    # ثم كل X ساعات
    schedule.every(CHECK_INTERVAL_HRS).hours.do(check_and_notify)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
