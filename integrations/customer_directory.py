from typing import Protocol


class CustomerDirectory(Protocol):
    def lookup_by_email(self, address: str) -> list[dict]:
        ...


class MockCustomerDirectory:
    def lookup_by_email(self, address: str) -> list[dict]:
        return [
            {
                "customer_id": "CUST-DEMO-001",
                "customer_name": "Teszt Ugyfel",
                "link_url": "https://example.local/customer/CUST-DEMO-001",
                "source": "mock",
            }
        ]
