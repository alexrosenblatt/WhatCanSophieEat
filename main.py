from flask import Flask, render_template, request
from model import IngredientNutrientResult
import fnmatch

app = Flask(__name__)


@app.route("/")
def index():
    """Initial rendering of search page. Sets initial search as blank in order to not render blank
    results box.."""
    search_query: str = ""
    return render_template("search.html", search_query=search_query)


@app.route("/", methods=["GET", "POST"])
def update():
    search_query = request.form["search_query"]
    try:
        NutrientResults = IngredientNutrientResult(search_query)
        NutrientResults.insert_results_into_cache()
    except KeyError:
        return render_template("search.html", search_query="", error=True)
    else:

        search_results = NutrientResults.parsed_nutrient_response
        fructose_serving_grams = round(
            NutrientResults.grams_fructose_per_single_serving_of_ingredient, 1
        )
        fructose_proportion = (
            NutrientResults.proportion_of_fructose_per_gram_of_ingredient
        )
        serving_unit_connecting_word = set_serving_unit_preposition(NutrientResults)
        can_eat = set_display_word_for_allowable_food(NutrientResults)

        return render_template(
            "search.html",
            search_query=search_query,
            query_response=search_results,
            t_fructose=NutrientResults.total_fructose,
            total_sugar_calc=NutrientResults.total_sugars_calculated,
            total_sugar_api=NutrientResults.total_sugar_from_api,
            serving_unit=NutrientResults.serving_unit,
            quantity=NutrientResults.quantity_of_servings,
            serving_size_grams=NutrientResults.total_weight_grams,
            name=NutrientResults.ingredient_name,
            can_eat=can_eat,
            under_limit=NutrientResults.is_under_allowable_fructose_limit,
            f_serving_grams=fructose_serving_grams,
            details=NutrientResults.has_detailed_nutrients,
            f_proportion=fructose_proportion,
            connecting_word=serving_unit_connecting_word,
        )


@app.route("/api/v1/get_single_ingredient", methods=["GET"])
def get_single_ingredient_result():
    if "search_query" in request.args:
        search_query = request.args["search_query"]
        try:
            NutrientResults = IngredientNutrientResult(search_query)
            # disabled due to lack of support for writing to sqlite3 dbs in Deta.sh
            # #todo - migrate to deta.sh db or new hosting service
            # NutrientResults.insert_results_into_cache()
        except KeyError:
            return render_template("search.html", search_query="", error=True)
        else:

            search_results = NutrientResults.parsed_nutrient_response
            fructose_serving_grams = round(
                NutrientResults.grams_fructose_per_single_serving_of_ingredient, 1
            )
            fructose_proportion = (
                NutrientResults.proportion_of_fructose_per_gram_of_ingredient
            )
            serving_unit_connecting_word = set_serving_unit_preposition(NutrientResults)
            can_eat = set_display_word_for_allowable_food(NutrientResults)

            return dict(
                search_query=search_query,
                query_response=search_results,
                t_fructose=NutrientResults.total_fructose,
                total_sugar_calc=NutrientResults.total_sugars_calculated,
                total_sugar_api=NutrientResults.total_sugar_from_api,
                serving_unit=NutrientResults.serving_unit,
                quantity=NutrientResults.quantity_of_servings,
                serving_size_grams=NutrientResults.total_weight_grams,
                name=NutrientResults.ingredient_name,
                can_eat=can_eat,
                under_limit=NutrientResults.is_under_allowable_fructose_limit,
                f_serving_grams=fructose_serving_grams,
                details=NutrientResults.has_detailed_nutrients,
                f_proportion=fructose_proportion,
                connecting_word=serving_unit_connecting_word,
            )
    else:
        return "Error: No query provided. Please specify a food."


def set_display_word_for_allowable_food(NutrientResults):
    if (
        NutrientResults.is_under_allowable_fructose_limit
    ):  # TODO maybe push this into Jinja?
        can_eat = "can"
    else:
        can_eat = "cannot"
    return can_eat


def set_serving_unit_preposition(NutrientResults):
    serving_unit = NutrientResults.serving_unit
    if (
        fnmatch.fnmatch(serving_unit.lower(), "*medium*")
        or fnmatch.fnmatch(serving_unit.lower(), "*small*")
        or fnmatch.fnmatch(serving_unit.lower(), "*large*")
    ):
        connecting_word = ""
    else:
        connecting_word = "of"
    return connecting_word
