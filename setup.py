from setuptools import setup

setup(name="dpaybot",
      version          = __import__('dpaybot').__version__,
      description      = "Testnet management scripts.",
      url              = "https://github.com/dpays/dpaybot",
      author           = "dPay Labs",
      packages         = ["dpaybot", "simple_dpay_client"],
      install_requires = [],
      entry_points     = {"console_scripts" : [
                          "dpaybot=dpaybot.main:sys_main",
                         ]}
    )
