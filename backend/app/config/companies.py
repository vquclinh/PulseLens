# Company universe — 8 tracked AI hardware / semiconductor companies
from dataclasses import dataclass, field
from typing import List


@dataclass
class Company:
    name: str
    ticker: str
    domain: str
    ir_url: str
    careers_url: str
    known_aliases: List[str] = field(default_factory=list)


COMPANIES: List[Company] = [
    Company(
        name="Nvidia",
        ticker="NVDA",
        domain="nvidia.com",
        ir_url="https://investor.nvidia.com",
        careers_url="https://nvidia.com/en-us/about-nvidia/careers/",
        known_aliases=["nvidia", "nvidia corporation", "NVDA"],
    ),
    Company(
        name="AMD",
        ticker="AMD",
        domain="amd.com",
        ir_url="https://ir.amd.com",
        careers_url="https://careers.amd.com",
        known_aliases=["amd", "advanced micro devices", "AMD"],
    ),
    Company(
        name="Intel",
        ticker="INTC",
        domain="intel.com",
        ir_url="https://investor.intel.com",
        careers_url="https://jobs.intel.com",
        known_aliases=["intel", "intel corporation", "INTC"],
    ),
    Company(
        name="Broadcom",
        ticker="AVGO",
        domain="broadcom.com",
        ir_url="https://investors.broadcom.com",
        careers_url="https://careers.broadcom.com",
        known_aliases=["broadcom", "broadcom inc", "AVGO"],
    ),
    Company(
        name="Supermicro",
        ticker="SMCI",
        domain="supermicro.com",
        ir_url="https://ir.supermicro.com",
        careers_url="https://www.supermicro.com/en/jobs",
        known_aliases=["supermicro", "super micro computer", "SMCI"],
    ),
    Company(
        name="Dell",
        ticker="DELL",
        domain="dell.com",
        ir_url="https://ir.dell.com",
        careers_url="https://jobs.dell.com",
        known_aliases=["dell", "dell technologies", "DELL"],
    ),
    Company(
        name="HPE",
        ticker="HPE",
        domain="hpe.com",
        ir_url="https://investor.hpe.com",
        careers_url="https://careers.hpe.com",
        known_aliases=["hpe", "hewlett packard enterprise", "HPE"],
    ),
    Company(
        name="Micron",
        ticker="MU",
        domain="micron.com",
        ir_url="https://investor.micron.com",
        careers_url="https://micron.com/careers",
        known_aliases=["micron", "micron technology", "MU"],
    ),
]

KNOWN_ENTITIES: set[str] = {"market"}
for _c in COMPANIES:
    KNOWN_ENTITIES.add(_c.name)
    KNOWN_ENTITIES.update(_c.known_aliases)
