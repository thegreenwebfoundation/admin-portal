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


class PartnerChoice(DjangoChoices):
    none = ChoiceItem('', 'None')
    partner = ChoiceItem('Partner', 'Partner')
    dev_partner = ChoiceItem('Dev Partner', 'Dev Partner')
    certified_gold = ChoiceItem('Certified Gold Partner', 'Certified Gold Partner')
    gold = ChoiceItem('Gold Partner', 'Gold Partner')


class ClassificationChoice(DjangoChoices):
    greengrid = ChoiceItem('GreenGrid', 'GreenGrid')
    energystart = ChoiceItem('EnergyStart', 'EnergyStart')
    breeam = ChoiceItem('BREEAM', 'BREEAM')
    leed = ChoiceItem('LEED', 'LEED')
    epa = ChoiceItem('EPA', 'EPA')
