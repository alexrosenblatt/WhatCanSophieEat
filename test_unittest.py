import unittest
from model import IngredientNutrientResult


class food_that_has_less_than_allowed_limit_fructose(unittest.TestCase):
    def setUp(self) -> None:
        self.search_object = IngredientNutrientResult("apple")
        self.search_object.grams_fructose_per_single_serving_of_ingredient = 0.0
        self.search_object.proportion_of_fructose_per_gram_of_ingredient = 0.0
        self.search_object.total_fructose = 2.5  # total fructose

        self.search_object.quantity_of_servings = 0.0
        self.search_object.serving_unit = ""
        self.search_object.total_weight_grams = 0.0
        self.search_object.ingredient_name = ""

        return super().setUp()

    def tests_detail_evaluation_correct_details_exist(self):
        self.search_object.total_sugars_calculated = 2.5
        self.search_object.total_sugar_from_api = 2.5
        result = self.search_object.evaluate_granular_nutrients_exist()
        self.assertEqual(result, True)

    def tests_fructose_limit_correctly_evaluated_with_details(self):
        self.search_object.total_sugars_calculated = 1
        self.search_object.total_sugar_from_api = 2.5
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, True)

    def tests_fructose_limit_correctly_evaluated_without_details(self):
        self.search_object.total_sugars_calculated = 0
        self.search_object.total_sugar_from_api = 2.5
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, True)


class food_that_has_greater_than_allowed_limit_fructose(unittest.TestCase):
    def setUp(self) -> None:
        self.search_object = IngredientNutrientResult("apple")
        self.search_object.grams_fructose_per_single_serving_of_ingredient = 0.0
        self.search_object.proportion_of_fructose_per_gram_of_ingredient = 0.0
        self.search_object.total_fructose = 3.5  # total fructose
        self.search_object.total_sugars_calculated = 0
        self.search_object.total_sugar_from_api = 0
        self.search_object.quantity_of_servings = 0.0
        self.search_object.serving_unit = ""
        self.search_object.total_weight_grams = 0.0
        self.search_object.ingredient_name = ""
        return super().setUp()

    def tests_detail_evaluation_no_details(self):
        self.search_object.total_sugars_calculated = 0
        self.search_object.total_sugar_from_api = 2.5
        result = self.search_object.evaluate_granular_nutrients_exist()
        self.assertEqual(result, False)

    def tests_fructose_limit_correctly_evaluated_for_greater_than_allowed_limit(self):
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, False)

    def tests_fructose_limit_correctly_evaluated_with_details_and_greater_than_allowed(
        self,
    ):
        self.search_object.total_sugars_calculated = 1
        self.search_object.total_sugar_from_api = 2.5
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, False)

    def tests_fructose_limit_correctly_evaluated_without_details_and_greater_than_allowed(
        self,
    ):
        self.search_object.total_sugars_calculated = 0
        self.search_object.total_sugar_from_api = 3.5
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, False)


class test_user_input(unittest.TestCase):
    def tests_user_submits_inedible_food(self):
        self.search_object = IngredientNutrientResult("1 apple")
        self.search_object.get_nutrient_raw_response()
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, False)

    def tests_user_submits_gibberish(self):
        self.search_object = IngredientNutrientResult("assfgasf")
        with self.assertRaises(KeyError):
            self.search_object.get_nutrient_raw_response()

    def tests_user_submits_only_numbers(self):
        self.search_object = IngredientNutrientResult("12413523314")
        with self.assertRaises(KeyError):
            self.search_object.get_nutrient_raw_response()

    def tests_user_submits_empty_string(self):
        self.search_object = IngredientNutrientResult("")
        with self.assertRaises(KeyError):
            self.search_object.get_nutrient_raw_response()

    def tests_user_submits_only_large_quantity(self):
        self.search_object = IngredientNutrientResult("12413523314 apples")
        self.search_object.get_nutrient_raw_response()
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, False)

    def tests_user_submits_only_0_of_something(self):
        self.search_object = IngredientNutrientResult("0 apples")
        self.search_object.get_nutrient_raw_response()
        result = (
            self.search_object.evaluate_if_ingredient_is_under_allowable_fructose_limit()
        )
        self.assertEqual(result, True)
