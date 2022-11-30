import json
import sqlite3
import logging
import requests  # type: ignore
from typing import Union
from decouple import config  # type: ignore

logging.basicConfig(filename="mainlog.log", encoding="utf-8", level=logging.NOTSET)

X_API_KEY = config("X_API_KEY")
X_APP_KEY = config("X_APP_KEY")


class IngredientNutrientResult:  # TODO should this be broken down in to subclasses?
    """Main class to handle each query."""

    def __init__(self, user_inputted_search_query: str):
        """Creates search object and returns nutrients of object.

        Args:
        - search_query(String) - user entered search text
        """
        self.search_query: str = user_inputted_search_query
        self.raw_response_from_api: str = ""
        self.full_response_api: dict = self.get_nutrient_raw_response()
        self.parsed_nutrient_response: dict[str, Union[float, str]] = {}

        self.grams_fructose_per_single_serving_of_ingredient: float = 0.0
        self.proportion_of_fructose_per_gram_of_ingredient: float = 0.0
        self.total_fructose: float = 0.0  # total fructose

        self.total_sugars_calculated: float = 0.0
        self.total_sugar_from_api: float = 0.0

        self.quantity_of_servings: float = 0.0
        self.serving_unit = ""
        self.total_weight_grams: float = 0.0

        self.ingredient_name = ""

        self.n_grams_fructose_allowed = 3

        self.populate_parsed_ingredient_results()
        self.set_allowable_limit_details()

    def set_allowable_limit_details(self):
        self.is_under_allowable_fructose_limit = (
            self.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        if not self.is_under_allowable_fructose_limit:
            (
                self.grams_fructose_per_single_serving_of_ingredient,
                self.proportion_of_fructose_per_gram_of_ingredient,
            ) = self.get_allowed_amount_of_ingredient_under_limit()

    def get_nutrient_raw_response(self) -> dict:
        """Main application logic to handle calling API or Cache and parsing response into nutrients. If "Demo" is set to true when CallAPI object created - a stubbed response is loaded, otherwise, it attempts to call the cache. If no matche exists, it queries the live API."""
        if not self.check_cache_for_match():
            logging.debug("no cache match")
            response = self.get_nutrient_data_from_api()
            logging.debug(f"result from api call{response}")
            return response
        else:
            response = self.get_nutrient_data_from_cache()
            if response is None:
                raise TypeError
            else:
                return response

    def populate_parsed_ingredient_results(self):
        (
            name,
            serving_unit,
            item,
            measure,
            quantity,
            serving_weight_grams,
            total_fructose,
            total_glucose,
            total_sucrose,
            total_sugar,
            total_fructose_calculated,
            total_glucose_calculated,
            total_sugar_calculated,
        ) = self.parse_nutrient_data()
        nutrient_response: dict[str, Union[float, str]] = {
            "name": name,
            "serving_unit": serving_unit,
            "serving_size_grams": serving_weight_grams,
            "item": item,
            "measure": measure,
            "quantity": quantity,
            "fructose": total_fructose,
            "glucose": total_glucose,
            "sucrose": total_sucrose,
            "t_fructose": total_fructose_calculated,
            "t_glucose": total_glucose_calculated,
            "t_sugar": total_sugar,
            "t_sugar_calc": total_sugar_calculated,
        }
        self.parsed_nutrient_response = nutrient_response
        self.total_fructose = float(total_fructose_calculated)
        self.total_sugars_calculated = float(total_sugar_calculated)
        self.total_sugar_from_api = float(total_sugar)
        self.serving_unit = serving_unit
        self.quantity_of_servings = float(quantity)
        self.total_weight_grams = float(serving_weight_grams)
        self.ingredient_name = name
        self.has_detailed_nutrients = self.evaluate_granular_nutrients_exist()

    def parse_nutrient_data(self):
        name = self.full_response_api["foods"][0]["food_name"]
        serving_unit = self.full_response_api["foods"][0]["serving_unit"]
        item = self.full_response_api["foods"][0]["tags"]["item"]
        measure = self.full_response_api["foods"][0]["tags"]["measure"]
        quantity = self.full_response_api["foods"][0]["tags"]["quantity"]
        serving_weight_grams = self.full_response_api["foods"][0][
            "serving_weight_grams"
        ]
        total_fructose = round(self.get_total_fructose(), 1)
        total_glucose = round(self.get_total_glucose(), 1)
        total_sucrose = round(self.get_total_sucrose(), 1)
        total_sugar = round(self.get_total_sugar(), 1)
        total_fructose_calculated = round(total_fructose + (total_sucrose / 2), 1)
        total_glucose_calculated = round(total_glucose + (total_sucrose / 2), 1)
        total_sugar_calculated = total_fructose + total_glucose + total_sucrose
        return (
            name,
            serving_unit,
            item,
            measure,
            quantity,
            serving_weight_grams,
            total_fructose,
            total_glucose,
            total_sucrose,
            total_sugar,
            total_fructose_calculated,
            total_glucose_calculated,
            total_sugar_calculated,
        )

    def insert_results_into_cache(self) -> bool:
        """Inserts query and search results into SQLlite DB using the response store in nute_response"""
        connection = sqlite3.connect("searches.db")
        f1 = self.search_query
        name_v = self.parsed_nutrient_response["name"]
        su_v = self.parsed_nutrient_response["serving_unit"]
        ss = self.parsed_nutrient_response["serving_size_grams"]
        i = self.parsed_nutrient_response["item"]
        m = self.parsed_nutrient_response["measure"]
        q = self.parsed_nutrient_response["quantity"]
        f = self.parsed_nutrient_response["fructose"]
        g = self.parsed_nutrient_response["glucose"]
        s = self.parsed_nutrient_response["sucrose"]
        raw = self.raw_response_from_api
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO searches (name,serving_unit,serving_size_grams,item,measure,quantity,fructose_n,glucose_n,sucrose,query,raw) VALUES (?,?,?,?,?,?,?,?,?,?,?);""",
            (name_v, su_v, ss, i, m, q, f, g, s, f1, raw),
        )
        connection.commit()
        logging.debug("Successfully wrote to cache")
        return True

    def get_nutrient_data_from_api(self) -> dict:
        """Handles the querying of the API, storing the response in json_response, and saving the last response to a text file for use in "demo mode"."""
        payload = json.dumps(
            {
                "query": self.search_query,
                "use_raw_foods": False,
                "include_subrecipe": False,
                "meal_type": 0,
                "use_branded_foods": False,
                "locale": "en_US",
                "taxonomy": False,
                "ingredient_statement": True,
                "last_modified": False,
            }
        )
        headers = {
            "x-app-key": X_API_KEY,
            "x-app-id": X_APP_KEY,
            "x-remote-user-id": "0",
            "Content-Type": "application/json",
        }
        raw_response_from_nutritionix_API = requests.post(
            "https://trackapi.nutritionix.com/v2/natural/nutrients",
            headers=headers,
            data=payload,
        )
        self.raw_response_from_api = raw_response_from_nutritionix_API.text
        response_json = json.loads(raw_response_from_nutritionix_API.text)
        logging.debug("Successful API call")
        logging.debug(response_json)
        return response_json

    def check_cache_for_match(self):
        connection = sqlite3.connect("searches.db")
        cursor = connection.cursor()
        sq = self.search_query.lower()
        logging.debug(f"User entered search: {self.search_query}")
        cursor.execute(
            "SELECT lower(raw) FROM Searches WHERE query = ? and raw != '' LIMIT 1",
            (sq,),
        )
        try:
            q = cursor.fetchone()[0]
            q = json.loads(q)
            if q != (None or {}):
                logging.debug("Match in cache")
                return True
            else:
                logging.debug("No match in cache")
                logging.debug(q)
                return False
        except:
            logging.debug("No match in cache - exception")
            return False

    def get_nutrient_data_from_cache(self) -> Union[dict, None]:
        connection = sqlite3.connect("searches.db")
        cursor = connection.cursor()
        sq = self.search_query.lower()
        logging.debug(f"Search query: {self.search_query}.")
        cursor.execute(
            "SELECT lower(raw) FROM Searches WHERE query = ? and raw != '' LIMIT 1",
            (sq,),
        )
        try:
            query = cursor.fetchone()[0]
            query = json.loads(query)
            if query != (None or {}):
                logging.debug("Returned response from cache")
                return query
            else:
                logging.debug("No match in cache - else")
                logging.debug(query)
                return None
        except:
            logging.debug("No match in cache - exception")
            return None

    def parse_ingredient_details(self) -> tuple:
        """Parses json response into fields to set class variables"""
        food_name = self.full_response_api["foods"][0]["food_name"]
        serving_unit = self.full_response_api["foods"][0]["serving_unit"]
        item = self.full_response_api["foods"][0]["tags"]["item"]
        measure = self.full_response_api["foods"][0]["tags"]["measure"]
        quantity = self.full_response_api["foods"][0]["tags"]["quantity"]
        serving_weight_grams = self.full_response_api["foods"][0][
            "serving_weight_grams"
        ]
        return food_name, serving_unit, serving_weight_grams, item, measure, quantity

    def extract_nutrient_details(self, nutrient_id: int) -> int:
        """Iterates over the set of nutrients in API response and returns the value for the nutrient id set in the attr_id param."""
        nutrient_value = 0
        nutrients = self.full_response_api["foods"][0]
        for nutrient in nutrients["full_nutrients"]:
            if nutrient["attr_id"] == nutrient_id:
                nutrient_value = nutrient["value"]
        if nutrient_value != 0:
            return nutrient_value
        else:
            return 0

    # TODO -  reduce these 5 methods dwon into a single list to pass into nutrient_search() method
    def get_total_fructose(self) -> int:
        nutrient_value = self.extract_nutrient_details(212)
        return nutrient_value

    def get_total_glucose(self) -> int:
        nutrient_value = self.extract_nutrient_details(211)
        return nutrient_value

    def get_total_sucrose(self) -> int:
        nutrient_value = self.extract_nutrient_details(210)
        return nutrient_value

    def get_total_sugar(self) -> int:
        nutrient_value = self.extract_nutrient_details(269)
        return nutrient_value

    def evaluate_if_ingredient_is_under_allowable_fructose_limit(self) -> bool:
        """Determines if a queried food is within fructose limit, handling the nuance of when the API returns granular sugar type details (details == True) and when it does not.
        If it does not, it defaults to using the overall sugar quantity. This is risk adverse, but safer."""

        if (
            self.has_detailed_nutrients
            and self.total_fructose <= self.n_grams_fructose_allowed
        ):
            self.is_under_allowable_fructose_limit = True
            return self.is_under_allowable_fructose_limit

        elif (
            not self.has_detailed_nutrients
            and self.total_sugar_from_api <= self.n_grams_fructose_allowed
        ):
            self.is_under_allowable_fructose_limit = True
            return self.is_under_allowable_fructose_limit
        else:
            self.is_under_allowable_fructose_limit = False
            return self.is_under_allowable_fructose_limit

    def evaluate_granular_nutrients_exist(self) -> bool:
        """Checks to see if granular details of sugars exist (quantity of any sugar is >0) and that the total sugar response from the API is not zero.
        If this is true, we can assume that the food is either: not devoid of sugar or the api did not return detailed sugar amounts."""
        if self.total_sugars_calculated == 0 and self.total_sugar_from_api != 0:
            has_detailed_nutrients = False
        else:
            has_detailed_nutrients = True
        print(f"detailed_nutrients is {has_detailed_nutrients}.")
        print(f"total_sugar_calc is {self.total_sugars_calculated}.")
        print(f"total_sugar_api is {self.total_sugar_from_api}.")
        return has_detailed_nutrients

    def get_allowed_amount_of_ingredient_under_limit(
        self,
    ) -> tuple[
        float,
        float,
    ]:  # TODO this more complicated than it needs to be - can probably refactor to simplify
        """Determines how much of a serving of a food can be eaten while keeping the quantity under the fructose limit."""
        # if api returns granular fructose use that - otherwise, use the total sugar quantity #TODO should likely handle this at the class level rather then in this method
        if self.total_fructose == 0:
            total_fructose_adjusted = self.total_sugar_from_api
        else:
            total_fructose_adjusted = self.total_fructose

        # determine amount of grams in a single serving by dividing the returned weight (n quantity of food) by the quantity (n)
        grams_single_serving = self.total_weight_grams / self.quantity_of_servings

        # determine amount of fructose in a single serving by dividing the returned amount of fructose (n quantity of food) by the quantity (n)
        fructose_single_serving = total_fructose_adjusted / self.quantity_of_servings

        # determine amount of fructose per gram of food by dividing the returned grams of fructose in a single serving by the grams of a single serving
        fructose_per_gram = fructose_single_serving / grams_single_serving

        # determine proportion of total allowed fructose within a single gram of food
        f_serving_grams = self.n_grams_fructose_allowed / fructose_per_gram
        serving_unit_proportion = f_serving_grams / grams_single_serving

        return f_serving_grams, serving_unit_proportion
