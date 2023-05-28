from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill

from .pyedaman import PyEdaman


class NutrientsSkill(OVOSSkill):
    def initialize(self):
        # free keys for the people
        if "recipes_appid" not in self.settings:
            self.settings["recipes_appid"] = 'eceecbfb'
        if "recipes_appkey" not in self.settings:
            self.settings["recipes_appkey"] = '83347a87348057d5ab183aade8106646'
        if "nutrition_appid" not in self.settings:
            self.settings["nutrition_appid"] = '5a32958e'
        if "nutrition_appkey" not in self.settings:
            self.settings["nutrition_appkey"] = 'cabec6b9addb1666e1365303e509f450'
        if "food_appid" not in self.settings:
            self.settings["nutrition_appid"] = "07d50733"
        if "food_appkey" not in self.settings:
            self.settings["nutrition_appkey"] = "80fcb49b500737827a9a23f7049653b9"

        self.edamam = PyEdaman(nutrition_appid=self.settings["nutrition_appid"],
                               nutrition_appkey=self.settings["nutrition_appkey"],
                               recipes_appid=self.settings["recipes_appid"],
                               recipes_appkey=self.settings["recipes_appkey"],
                               food_appid=self.settings["food_appid"],
                               food_appkey=self.settings["food_appkey"])

    @intent_handler("ingredients.intent")
    def handle_ingredients_intent(self, message):
        sentence = message.data["sentence"]
        # TODO use dialog file
        for recipe in e.search_recipe(sentence):
            sentences = (f["text"] for f in recipe.ingredient_quantities)
            self.enclosure.deactivate_mouth_events()
            for idx, s in enumerate(sentences):
                if idx >= 2:
                    self.enclosure.deactivate_mouth_events()
                    self.enclosure.mouth_text(s)
                self.speak(s, wait=True)
            self.enclosure.activate_mouth_events()
            break
        else:
            # TODO dialog file
            self.speak("unknown food")

    @intent_handler("calories.intent")
    def handle_calories_intent(self, message):
        sentence = message.data["sentence"]
        for nutrient_data in e.search_nutrient(sentence):
            # TODO dialog file
            speak = f"{nutrient_data} has {nutrient_data.calories} calores"
            self.speak(speak)
            break
        else:
            query = "1 gram of " + sentence
            for nutrient_data in e.search_nutrient(query):
                # TODO dialog file
                speak = f"{nutrient_data} has {nutrient_data.calories} calores"
                self.speak(speak)
                break
            else:
                # TODO dialog file
                self.speak("unknown food")
