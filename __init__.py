from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill
from py_edamam import Edaman


class NutrientsSkill(OVOSSkill):
    def initialize(self):
        # free keys for the people
        if "recipes_appid" not in self.settings:
            self.settings["recipes_appid"] = 'eceecbfb'
        if "recipes_appkey" not in self.settings:
            self.settings["recipes_appkey"] = \
                '83347a87348057d5ab183aade8106646'
        if "nutrition_appid" not in self.settings:
            self.settings["nutrition_appid"] = '5a32958e'
        if "nutrition_appkey" not in self.settings:
            self.settings["nutrition_appkey"] = \
                'cabec6b9addb1666e1365303e509f450'

        self.edamam = Edaman(nutrition_appid=self.settings["nutrition_appid"],
                             nutrition_appkey=self.settings["nutrition_appkey"],
                             recipes_appid=self.settings["recipes_appid"],
                             recipes_appkey=self.settings["recipes_appkey"])

    @intent_handler("ingredients.intent")
    def handle_ingredients_intent(self, message):
        sentence = message.data["sentence"]
        # TODO use dialog file
        sentences = self.edamam.pretty_nutrient(sentence).split("\n")
        self.enclosure.deactivate_mouth_events()
        for idx, s in enumerate(sentences):
            if idx >= 2:
                self.enclosure.deactivate_mouth_events()
                self.enclosure.mouth_text(s)
            self.speak(s, wait=True)

        self.enclosure.activate_mouth_events()

    @intent_handler("calories.intent")
    def handle_calories_intent(self, message):
        sentence = message.data["sentence"]
        n = self.edamam.search_nutrient(sentence)
        if n is None:
            query = "1 gram of " + sentence
            n = self.edamam.search_nutrient(query)
            n["name"] = "1 gram of " + n["name"]
        if n is not None:
            # TODO dialog file
            self.speak(n["name"] + " has " + str(n["calories"]) + " calories")
        else:
            # TODO dialog file
            self.speak("unknown food")
