from numbers import Number
import os, logging, requests
from config import Config
import pandas as pd


class GHGCalculator:
    __slots__ = (
        "region",
        "estimation_endpoint",
        "search_endpoint",
        "ghgs",
        "emission_factors",
        "currency",
        "api_auth",
        "consumer_price_index",
        "version"
    )

    def __init__(self, region: str, currency: str):
        url = "https://beta4.api.climatiq.io"
        self.estimation_endpoint = f"{url}/estimate"
        self.search_endpoint = f"{url}/search"
        api_key = os.environ.get("CALCULATIONS_API_KEY")
        self.api_auth = {"Authorization": f"Bearer: {api_key}"}
        config = Config()
        self.ghgs = config.greenhouse_gasses
        self.consumer_price_index = pd.read_csv(
            str(config.data_dir / "average-cpis.csv")
        )
        self.currency = currency
        self.region = region
        self.version = config.api_data_version

    @property
    def unit_types_to_unit(self):
        return {
            "money": self.currency,
            "energy": "kwh",
        }

    def calc_inflation(self, value, factor_region, factor_year):
        cpis = self.consumer_price_index
        region = cpis[cpis["region_code"] == factor_region]
        old_cpi = next(iter(region.loc[:, str(factor_year)]))
        current_cpi = next(
            iter(
                region.loc[
                    :, str(2023)
                ]  # TODO: only have inflation data to 2023, and how do we automate the updates of it?
            )
        )
        real = value * (old_cpi / current_cpi)
        return real

    def get_possible_queries(self, queries: dict) -> dict:
        """This endpoint returns the possibilites of stricter query combinations 
        (year, region, etc) given a set of query params already in place
        """
        return requests.get(
            url=self.search_endpoint, params=queries, headers=self.api_auth
        ).json()

    def get_best_query(self, activity_id: str) -> int:
        # TODO: consider either region fallback or year fallback parameter instead of this, especially if it's faster
        """Logic to get the most recent year available for an emission factor
        given the user's region. Falls back to latest year if the region
        doesn't have a factor
        """

        queries = {
            "activity_id": activity_id,
            "data_version": self.version,
            "region": self.region,
        }
        valid_queries = self.get_possible_queries(queries=queries)
        if valid_queries["total_results"] < 1:
            logging.warning(
                "No corresponding emission factor for the given region"
                f" `{self.region}` falling back to latest year"
            )
            queries.pop("region")
            valid_queries = self.get_possible_queries(queries=queries)
        best_match = max(valid_queries["results"], key=lambda x: x["year"])
        return best_match

    def format_request(
        self, activity_id: str, value: Number, unit_type: str, unit: str
    ) -> dict:
        """Get a request ready for the emissions estimation endpoint"""

        best_match = self.get_best_query(activity_id=activity_id)
        # account inflation w.r.t the emission factor's region and year
        real_value = self.calc_inflation(
            value=value,
            factor_region=best_match["region"],
            factor_year=best_match["year"],
        )

        parameters = {unit_type: real_value, f"{unit_type}_unit": unit}
        data = {
            "emission_factor": {
                "id": best_match["id"],
            },
            "parameters": parameters,
        }
        return data

    def format_response(self, res: dict) -> dict:
        """Extract the wanted info from api response"""
        emissions = res["constituent_gases"]
        print(emissions, "constituent gases")
        emissions = {
            "co2e": res["co2e"], 
            "co2e_unit": res["co2e_unit"],
            **{g: emissions.get(g) for g in self.ghgs}
        }
        return emissions

    # CALCULATE FOR INFLATION AND PURCHASE VS BASIC PRICE https://www.climatiq.io/docs/guides/understanding/procurement-spend-based-calculations FOR EXIOBASE
    
    def to_kg(
        value: Number, unit: str, conversions: dict = {
            "g": 0.001, "t": 1000, 
        }
    ) -> Number:
        """Turn the co2e value from api response into kilograms to have 
        one standard unit across all operations"""
        if unit == "kg":
            return value
        elif unit == "g":
            return value * 0.001
        elif unit == "t":
            return value * 1000
        

    def __call__(
        self, value: Number, activity_id: str, unit_type: str, unit: str | None = None
    ) -> dict:
        """Returns ghg emissions given an activity and a value
        representing the `amount` of activity done

        Args:
            value: the numerical representation of the activity e.g 5 for 5 dollars
            activity: the activity to get the emission factor for
            unit_type: the type of unit either money or weight 
            unit: the specific unit if unit type is not money - kg, lb, g

        Returns: The given emissions for the ghgs with available factors
        """
        # unit = unit or self.unit_types_to_unit[unit_type]
        # request = self.format_request(
        #     activity_id=activity_id, value=value, unit=unit, unit_type=unit_type
        # )
        # res = requests.post(
        #     url=self.estimation_endpoint, headers=self.api_auth, json=request
        # )
        # return self.format_response(res.json())
        import random
        return {
            "co2e": random.randint(0, value * 1.5),
            "ch4": None,
            "co2": None,
            "n2o": None
        }
