from djchoices import DjangoChoices, ChoiceItem


class EnergyType(DjangoChoices):
    wind = ChoiceItem()
    water = ChoiceItem()
    solar = ChoiceItem()
    mixed = ChoiceItem()


class TempType(DjangoChoices):
    C = ChoiceItem()
    F = ChoiceItem()


class ModelType(DjangoChoices):
    green_energy = ChoiceItem('groeneenergie')
    compensation = ChoiceItem('compensatie')
