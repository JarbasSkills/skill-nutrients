import json
import logging

import cloudscraper
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("PyEdamam")


class APIError(Exception):
    """ raised when api requests fail """


class LowQualityQuery(APIError):
    """ raised when query is not understood """


class InvalidKey(APIError):
    """ raised when keys are invalid """


class InvalidFoodApiKey(InvalidKey):
    """ raised when food api keys are invalid """


class InvalidRecipeApiKey(InvalidKey):
    """ raised when recipe api keys are invalid """


class InvalidNutrientsApiKey(InvalidKey):
    """ raised when nutrients api keys are invalid """


class Edaman:
    """ low level api returning raw json data"""

    def __init__(self,
                 # keys scrapped from web demos
                 nutrition_appid="47379841",
                 nutrition_appkey="d28718060b8adfd39783ead254df7f92",
                 recipes_appid='eceecbfb',
                 recipes_appkey='83347a87348057d5ab183aade8106646',
                 food_appid="07d50733",
                 food_appkey="80fcb49b500737827a9a23f7049653b9"
                 ):
        self.nutrition_appid = nutrition_appid
        self.nutrition_appkey = nutrition_appkey
        self.recipes_appid = recipes_appid
        self.recipes_appkey = recipes_appkey
        self.food_appid = food_appid
        self.food_appkey = food_appkey

    def search_recipe(self, query="chicken"):
        url = 'https://api.edamam.com/search?q=' + query + '&app_id=' + \
              self.recipes_appid + '&app_key=' + \
              self.recipes_appkey

        r = requests.get(url)
        if r.status_code == 401:
            logger.error("invalid recipe api key")
            raise InvalidRecipeApiKey
        return r.json()

    def search_nutrient(self, ingredients=None):
        ingredients = ingredients or []
        if isinstance(ingredients, str):
            ingredients = [ingredients]

        url = 'https://api.edamam.com/api/nutrition-details?app_id={id}' \
              '&app_key={key}'.format(id=self.nutrition_appid,
                                      key=self.nutrition_appkey)

        data = {"ingr": ingredients}
        r = requests.post(url,
                          headers={"Content-Type": "application/json"},
                          data=json.dumps(data))

        if r.status_code == 401:
            logger.error("invalid nutrients api key")
            raise InvalidNutrientsApiKey

        data = r.json()
        if data.get("error"):
            if data["error"] == "low_quality":
                logger.error("could not understand query")
                raise LowQualityQuery
            else:
                raise APIError
        return data

    def search_food(self, query="pizza"):
        url = 'https://api.edamam.com/api/food-database/parser?nutrition' \
              '-type=logging&ingr={query}&app_id={id}&app_key={key}' \
            .format(id=self.food_appid, key=self.food_appkey, query=query)

        r = requests.get(url)
        if r.status_code == 401:
            logger.error("invalid food api key")
            raise InvalidFoodApiKey

        r = r.json()
        if r.get("status") == "error":
            error = r.get("message")
            if not error:
                error = "Api request failed"
            logger.error(error)
            raise APIError
        return r


class PyEdaman(Edaman):
    """ High level api generating data objects"""

    def search_recipe(self, query):
        data = super().search_recipe(query)
        hits = data["hits"]
        for hit in hits:
            data = hit["recipe"]
            data["yields"] = data["yield"]
            data.pop("yield")
            data["ingredient_names"] = data["ingredientLines"]
            data.pop("ingredientLines")
            data["share_url"] = data["shareAs"]
            data.pop("shareAs")
            print(list(data.keys()))
            yield Recipe(edamam=self, **data)

    def search_nutrient(self, ingredients=None):
        ingredients = ingredients or []
        if isinstance(ingredients, str):
            ingredients = [ingredients]
        for ing in ingredients:
            data = super().search_nutrient(ing)
            data["yields"] = data["yield"]
            data.pop("yield")
            yield Ingredient(name=ing, **data)

    def search_food(self, query):
        data = super().search_food(query)
        for food in data["parsed"]:
            yield Food(measure=food["measure"],
                       quantity=food["quantity"],
                       **food["food"])


# Data classes
class Measure:
    def __init__(self, label, uri,
                 **kwargs):
        self.label = label
        self.uri = uri

    def __repr__(self):
        return self.label


class Nutrient:
    """ A nutrient in some food"""

    def __init__(self, tag, label=None, quantity=0, unit=None,
                 **kwargs):
        self.tag = tag
        self.label = label or tag
        self.quantity = quantity
        self.unit = unit

    def __repr__(self):
        if self.unit:
            name = "{label} * {quantity} {unit}".format(label=self.label,
                                                        quantity=self.quantity,
                                                        unit=self.unit)
        else:
            name = "{quantity} * {label}".format(label=self.label,
                                                 quantity=self.quantity)
        return name


class Ingredient:
    """ Nutritional data about an ingredient of some food """

    def __init__(self,
                 name,
                 uri="",
                 dietLabels=None,
                 healthLabels=None,
                 yields=1.0,
                 cautions=None,
                 totalDaily=None,
                 totalWeight=0,
                 calories=0,
                 totalNutrients=None,
                 totalNutrientsKCal=None,
                 **kwargs):
        self.name = name
        self.dietLabels = dietLabels or []
        self.healthLabels = healthLabels or []
        self.uri = uri
        self.yields = yields
        self.cautions = cautions
        self.totalDaily = []
        if isinstance(totalDaily, dict):
            for n in totalDaily:
                self.totalDaily += [Nutrient(n, **totalDaily[n])]
        else:
            self.totalDaily = totalDaily or []
        self.totalWeight = totalWeight
        self.totalNutrientsKCal = []
        if isinstance(totalNutrientsKCal, dict):
            for n in totalNutrientsKCal:
                self.totalNutrientsKCal += [Nutrient(n, **totalNutrientsKCal[n])]
        else:
            self.totalNutrientsKCal = totalNutrientsKCal or []
        self.calories = calories
        self.totalNutrients = []
        if isinstance(totalNutrients, dict):
            for n in totalNutrients:
                self.totalNutrients += [Nutrient(n, **totalNutrients[n])]
        else:
            self.totalNutrients = totalNutrients or []

    def __str__(self):
        return self.name


class Food:
    """ something you can eat """

    def __init__(self, foodId, label="",
                 category="Generic foods",
                 categoryLabel="",
                 measure=None,
                 quantity=1,
                 nutrients=None,
                 image=None,
                 **kwargs):
        self.foodId = foodId
        self.label = label
        self.category = category
        self.categoryLabel = categoryLabel
        if isinstance(measure, dict):
            measure = Measure(**measure)
        self.measure = measure
        self.nutrients = []
        if isinstance(nutrients, dict):
            for n in nutrients:
                self.nutrients += [Nutrient(n, quantity=nutrients[n])]
        else:
            self.nutrients = nutrients or []
        self.quantity = quantity
        self.image = image

    def __str__(self):
        if self.quantity != 1:
            return str(self.quantity) + " * " + self.label
        return self.label


class Recipe:
    def __init__(self,
                 label,
                 uri="",
                 url="",
                 share_url="",
                 image=None,
                 dietLabels=None,
                 healthLabels=None,
                 yields=1.0,
                 cautions=None,
                 totalDaily=None,
                 totalWeight=0,
                 calories=0,
                 totalTime=0,
                 totalNutrients=None,
                 digest=None,
                 ingredients=None,
                 source="edaman",
                 ingredient_names=None,
                 edamam=None,
                 cuisineType=None,
                 mealType=None,
                 dishType=None, ):
        self.ingredient_names = ingredient_names or []
        self.ingredient_quantities = ingredients or []
        self.cuisineType = cuisineType or []
        self.mealType = mealType or []
        self.dishType = dishType or []
        self.label = label
        self.dietLabels = dietLabels or []
        self.healthLabels = healthLabels or []
        self.uri = uri
        self.url = url or self.uri
        self.share_url = share_url or self.url
        self.source = source
        self.yields = yields
        self.cautions = cautions
        self.totalDaily = []
        if isinstance(totalDaily, dict):
            for n in totalDaily:
                self.totalDaily += [Nutrient(n, **totalDaily[n])]
        else:
            self.totalDaily = totalDaily or []
        self.totalWeight = totalWeight
        self.calories = calories
        self.totalTime = totalTime
        self.totalNutrients = []
        if isinstance(totalNutrients, dict):
            for n in totalNutrients:
                self.totalNutrients += [Nutrient(n, **totalNutrients[n])]
        else:
            self.totalNutrients = totalNutrients or []
        self.image = image
        if isinstance(digest, list):
            self.digest = {}
            for content in digest:
                self.digest[content["label"]] = content
        else:
            self.digest = digest or {}
        self.__edamam = edamam or Edaman()

    def get_ingredients_data(self):
        for ing in self.__edamam.search_nutrient(self.ingredient_names):
            yield ing

    def parse(self):
        return self._get_recipe_instructions(self.source.lower().replace(" ", ""), self.url)

    def _get_recipe_instructions(self, source, source_url):
        results = []
        final_results = []
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(source_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = self._get_provider_result(source, soup)

        for item in results:
            if item not in final_results:
                final_results.append({"step": item})

        return final_results

    def _get_provider_result(self, provider_source, soup):
        print(provider_source)
        try:
            results = []
            if provider_source == 'food52':
                extractor = soup.find("div", {"class": "recipe__list--steps"})
                steps = extractor.find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == 'epicurious':
                extractor = soup.find(
                    "script", {"type": "application/ld+json"})
                json_data = json.loads(extractor.contents[0])
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "seriouseats":
                extractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                data_source = extractor[0].contents[0]
                json_data = json.loads(data_source)
                for data in json_data:
                    steps = data.get("recipeInstructions", "")
                    if steps:
                        for step in steps:
                            text = step.get("text", "")
                            results.append(text)

            if provider_source == "marthastewart":
                extractor = soup.find("ul", {"class": "instructions-section"})
                steps = extractor.find_all("li")

                for step in steps:
                    step_additional_a = step.find(
                        "div", {"class": "section-body"})
                    step_additional_b = step_additional_a.find("p")
                    results.append(step_additional_b.text)

            if provider_source == "whiteonricecouple":
                extractor = soup.find(
                    "script", {"type": "application/ld+json"})
                json_data = json.loads(extractor.contents[0])
                data_filter = json_data["@graph"]
                for data in data_filter:
                    if data["@type"] == "Recipe":
                        steps = data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            if provider_source == "bonappetit":
                extractor = soup.find(
                    "script", {"type": "application/ld+json"})
                json_data = json.loads(extractor.contents[0])
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "tastingtable":
                extractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                json_data = json.loads(extractor[1].contents[0])
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "honestcooking":
                extractor = soup.find_all(
                    "li", {"itemprop": "recipeInstructions"})
                for step in extractor:
                    results.append(step.text)

            if provider_source == "foodandwine":
                extractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(extractor.contents[0])
                json_data = data[0]
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "eatingwell":
                exctractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(exctractor.contents[0])
                json_data = data[1]
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "cookstr":
                extractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                json_data = json.loads(extractor[1].contents[0])
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "bbcgoodfood":
                exctractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(exctractor.contents[0])
                steps = data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "delish":
                exctractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(exctractor.contents[0])
                steps = data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "pioneerwoman":
                exctractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(exctractor.contents[0])
                steps = data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "foodnetwork":
                exctractor = soup.find(
                    "script", {"type": "application/ld+json"})
                data = json.loads(exctractor.contents[0])
                json_data = data[0]
                steps = json_data["recipeInstructions"]

                for step in steps:
                    text = step.get("text", "")
                    results.append(text)

            if provider_source == "closetcooking":
                exctractor = soup.find("ol", {"class": "instructions"})
                steps = exctractor.find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == "cookalmostanything":
                exctractor = soup.find("div", {"class": "post-body"})
                for s in exctractor.find_all("center"):
                    s.decompose()
                steps = exctractor.get_text().split("<br>")
                for step in steps:
                    results.append(step)

            if provider_source == "bbc":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step)

            if provider_source == "foodrepublic":
                exctractor = soup.find(
                    "span", {"itemprop": "recipeInstructions"})
                steps = exctractor.find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == "simplyrecipes":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    data = json_data[0]
                    if "recipeInstructions" in data:
                        steps = data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            if provider_source == "latimes":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            if provider_source == "thedailymeal":
                exctractor = soup.find("ol", {"class": "recipe-directions"})
                steps = exctractor.find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == "saveur":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            if provider_source == "frenchrevolutionfood":
                exctractor = soup.find("div", {"class": "recipe"})
                orderedlist = exctractor.find_all("ol")
                steps = orderedlist[0].find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == "food.com":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            if provider_source == "foodista":
                exctractor = soup.findAll("div", {"class": "step-body"})
                for step in exctractor:
                    results.append(step.text)

            if provider_source == "turniptheoven.com":
                extractor = soup.find("ol", {"itemprop": "recipeInstructions"})
                steps = extractor.find_all("li")

                for step in steps:
                    results.append(step.text)

            if provider_source == "tastykitchen.com":
                exctractor = soup.find("span", {"itemprop": "instructions"})
                steps = exctractor.find_all("p")

                for step in steps:
                    results.append(step.text)

            if provider_source == "nomnompaleo":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    graph_data = json_data["@graph"]
                    for data in graph_data:
                        if "recipeInstructions" in data:
                            steps = data["recipeInstructions"]
                            for step in steps:
                                results.append(step.get("text", ""))

            if provider_source == "justapinch.com":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step)

            if provider_source == "foxeslovelemons.com":
                exctractor = soup.findAll(
                    "script", {"type": "application/ld+json"})
                for data in exctractor:
                    json_data = json.loads(data.contents[0])
                    if "recipeInstructions" in json_data:
                        steps = json_data["recipeInstructions"]
                        for step in steps:
                            results.append(step.get("text", ""))

            results = [item.strip() for item in results if item.strip()]
            return results

        except Exception as e:
            print("Error Getting Recipe Instructions: %s", e)
            return []

    def __str__(self):
        return self.label


if __name__ == "__main__":

    e = PyEdaman()

    for recipe in e.search_recipe("onion and chicken"):
        print(recipe, recipe.url)
        print(recipe.parse())
