from enum import Enum


class TradeSymbol(str, Enum):
    ADVANCED_CIRCUITRY = "ADVANCED_CIRCUITRY"
    AI_MAINFRAMES = "AI_MAINFRAMES"
    ALUMINUM = "ALUMINUM"
    ALUMINUM_ORE = "ALUMINUM_ORE"
    AMMONIA_ICE = "AMMONIA_ICE"
    AMMUNITION = "AMMUNITION"
    ANTIMATTER = "ANTIMATTER"
    ASSAULT_RIFLES = "ASSAULT_RIFLES"
    BIOCOMPOSITES = "BIOCOMPOSITES"
    BOTANICAL_SPECIMENS = "BOTANICAL_SPECIMENS"
    CLOTHING = "CLOTHING"
    COPPER = "COPPER"
    COPPER_ORE = "COPPER_ORE"
    CULTURAL_ARTIFACTS = "CULTURAL_ARTIFACTS"
    CYBER_IMPLANTS = "CYBER_IMPLANTS"
    DIAMONDS = "DIAMONDS"
    DRUGS = "DRUGS"
    ELECTRONICS = "ELECTRONICS"
    ENGINE_HYPER_DRIVE_I = "ENGINE_HYPER_DRIVE_I"
    ENGINE_IMPULSE_DRIVE_I = "ENGINE_IMPULSE_DRIVE_I"
    ENGINE_ION_DRIVE_I = "ENGINE_ION_DRIVE_I"
    ENGINE_ION_DRIVE_II = "ENGINE_ION_DRIVE_II"
    EQUIPMENT = "EQUIPMENT"
    EXOTIC_MATTER = "EXOTIC_MATTER"
    EXPLOSIVES = "EXPLOSIVES"
    FABRICS = "FABRICS"
    FERTILIZERS = "FERTILIZERS"
    FIREARMS = "FIREARMS"
    FOOD = "FOOD"
    FUEL = "FUEL"
    GENE_THERAPEUTICS = "GENE_THERAPEUTICS"
    GOLD = "GOLD"
    GOLD_ORE = "GOLD_ORE"
    GRAVITON_EMITTERS = "GRAVITON_EMITTERS"
    HOLOGRAPHICS = "HOLOGRAPHICS"
    HYDROCARBON = "HYDROCARBON"
    ICE_WATER = "ICE_WATER"
    IRON = "IRON"
    IRON_ORE = "IRON_ORE"
    JEWELRY = "JEWELRY"
    LAB_INSTRUMENTS = "LAB_INSTRUMENTS"
    LASER_RIFLES = "LASER_RIFLES"
    LIQUID_HYDROGEN = "LIQUID_HYDROGEN"
    LIQUID_NITROGEN = "LIQUID_NITROGEN"
    MACHINERY = "MACHINERY"
    MEDICINE = "MEDICINE"
    MERITIUM = "MERITIUM"
    MERITIUM_ORE = "MERITIUM_ORE"
    MICROPROCESSORS = "MICROPROCESSORS"
    MICRO_FUSION_GENERATORS = "MICRO_FUSION_GENERATORS"
    MILITARY_EQUIPMENT = "MILITARY_EQUIPMENT"
    MODULE_CARGO_HOLD_I = "MODULE_CARGO_HOLD_I"
    MODULE_CREW_QUARTERS_I = "MODULE_CREW_QUARTERS_I"
    MODULE_ENVOY_QUARTERS_I = "MODULE_ENVOY_QUARTERS_I"
    MODULE_FUEL_REFINERY_I = "MODULE_FUEL_REFINERY_I"
    MODULE_JUMP_DRIVE_I = "MODULE_JUMP_DRIVE_I"
    MODULE_JUMP_DRIVE_II = "MODULE_JUMP_DRIVE_II"
    MODULE_JUMP_DRIVE_III = "MODULE_JUMP_DRIVE_III"
    MODULE_MICRO_REFINERY_I = "MODULE_MICRO_REFINERY_I"
    MODULE_MINERAL_PROCESSOR_I = "MODULE_MINERAL_PROCESSOR_I"
    MODULE_ORE_REFINERY_I = "MODULE_ORE_REFINERY_I"
    MODULE_PASSENGER_CABIN_I = "MODULE_PASSENGER_CABIN_I"
    MODULE_SCIENCE_LAB_I = "MODULE_SCIENCE_LAB_I"
    MODULE_SHIELD_GENERATOR_I = "MODULE_SHIELD_GENERATOR_I"
    MODULE_SHIELD_GENERATOR_II = "MODULE_SHIELD_GENERATOR_II"
    MODULE_WARP_DRIVE_I = "MODULE_WARP_DRIVE_I"
    MODULE_WARP_DRIVE_II = "MODULE_WARP_DRIVE_II"
    MODULE_WARP_DRIVE_III = "MODULE_WARP_DRIVE_III"
    MOOD_REGULATORS = "MOOD_REGULATORS"
    MOUNT_GAS_SIPHON_I = "MOUNT_GAS_SIPHON_I"
    MOUNT_GAS_SIPHON_II = "MOUNT_GAS_SIPHON_II"
    MOUNT_GAS_SIPHON_III = "MOUNT_GAS_SIPHON_III"
    MOUNT_LASER_CANNON_I = "MOUNT_LASER_CANNON_I"
    MOUNT_MINING_LASER_I = "MOUNT_MINING_LASER_I"
    MOUNT_MINING_LASER_II = "MOUNT_MINING_LASER_II"
    MOUNT_MINING_LASER_III = "MOUNT_MINING_LASER_III"
    MOUNT_MISSILE_LAUNCHER_I = "MOUNT_MISSILE_LAUNCHER_I"
    MOUNT_SENSOR_ARRAY_I = "MOUNT_SENSOR_ARRAY_I"
    MOUNT_SENSOR_ARRAY_II = "MOUNT_SENSOR_ARRAY_II"
    MOUNT_SENSOR_ARRAY_III = "MOUNT_SENSOR_ARRAY_III"
    MOUNT_SURVEYOR_I = "MOUNT_SURVEYOR_I"
    MOUNT_SURVEYOR_II = "MOUNT_SURVEYOR_II"
    MOUNT_SURVEYOR_III = "MOUNT_SURVEYOR_III"
    MOUNT_TURRET_I = "MOUNT_TURRET_I"
    NANOBOTS = "NANOBOTS"
    NEURAL_CHIPS = "NEURAL_CHIPS"
    NOVEL_LIFEFORMS = "NOVEL_LIFEFORMS"
    PLASTICS = "PLASTICS"
    PLATINUM = "PLATINUM"
    PLATINUM_ORE = "PLATINUM_ORE"
    POLYNUCLEOTIDES = "POLYNUCLEOTIDES"
    PRECIOUS_STONES = "PRECIOUS_STONES"
    QUANTUM_DRIVES = "QUANTUM_DRIVES"
    QUARTZ_SAND = "QUARTZ_SAND"
    REACTOR_ANTIMATTER_I = "REACTOR_ANTIMATTER_I"
    REACTOR_CHEMICAL_I = "REACTOR_CHEMICAL_I"
    REACTOR_FISSION_I = "REACTOR_FISSION_I"
    REACTOR_FUSION_I = "REACTOR_FUSION_I"
    REACTOR_SOLAR_I = "REACTOR_SOLAR_I"
    RELIC_TECH = "RELIC_TECH"
    ROBOTIC_DRONES = "ROBOTIC_DRONES"
    SHIP_PLATING = "SHIP_PLATING"
    SHIP_SALVAGE = "SHIP_SALVAGE"
    SILICON_CRYSTALS = "SILICON_CRYSTALS"
    SILVER = "SILVER"
    SILVER_ORE = "SILVER_ORE"
    SUPERGRAINS = "SUPERGRAINS"
    URANITE = "URANITE"
    URANITE_ORE = "URANITE_ORE"
    VIRAL_AGENTS = "VIRAL_AGENTS"

    def __str__(self) -> str:
        return str(self.value)