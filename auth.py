import random
import string


def generate_passcode():
    return ''.join(random.choices(string.digits, k=6))

def send_passcode(email, passcode):
    print(f"[DEV] Passcode for {email}: {passcode}")
