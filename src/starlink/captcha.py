from os import getenv
from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless

class CaptchaSolver:
    def __init__(self, site_url: str):
        self.api_key = getenv("CAPTCHA_API_KEY")
        self.site_url = site_url
    
    def solve(self, site_key: str) -> str:
        solver = hCaptchaProxyless()
        solver.set_verbose(1)
        solver.set_key(self.api_key)
        solver.set_website_url(self.site_url)
        solver.set_website_key(site_key)
        solver.set_is_invisible(True)
        g_response = solver.solve_and_return_solution()
        if g_response == 0:
            raise Exception(solver.error_code)
        return str(g_response)