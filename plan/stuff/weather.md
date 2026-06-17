# Weather Conditions - Text-Based RPG

## Normal Conditions

### Clear Skies
- **ID**: clear_skies
- **Temperature Effect**: 0 degrees
- **Humidity**: Low
- **Visibility**: 100%
- **Movement Speed**: 100%
- **Combat Effects**: None; perfect conditions for ranged combat
- **Duration**: 6-12 hours
- **Biomes**: All biomes
- **Special Events**: None

### Partly Cloudy
- **ID**: partly_cloudy
- **Temperature Effect**: -2 degrees
- **Humidity**: Low
- **Visibility**: 90%
- **Movement Speed**: 100%
- **Combat Effects**: None
- **Duration**: 4-8 hours
- **Biomes**: All biomes
- **Special Events**: None

### Overcast
- **ID**: overcast
- **Temperature Effect**: -5 degrees
- **Humidity**: Medium
- **Visibility**: 75%
- **Movement Speed**: 95%
- **Combat Effects**: None; slightly reduced ranged accuracy due to gloom
- **Duration**: 4-10 hours
- **Biomes**: All biomes
- **Special Events**: May precede rain or snow

### Light Breeze
- **ID**: light_breeze
- **Temperature Effect**: -3 degrees
- **Humidity**: Low
- **Visibility**: 100%
- **Movement Speed**: 100%
- **Combat Effects**: None; may slightly deflect long-range projectiles
- **Duration**: 2-6 hours
- **Biomes**: Plains, coastal areas
- **Special Events**: None

### Windy
- **ID**: windy
- **Temperature Effect**: -7 degrees
- **Humidity**: Low
- **Visibility**: 85%
- **Movement Speed**: 90%
- **Combat Effects**: Ranged attacks have -10% accuracy; light characters may be pushed
- **Duration**: 3-8 hours
- **Biomes**: Plains, mountain peaks, coastal areas
- **Special Events**: May knock over loose objects

### Gusty Winds
- **ID**: gusty_winds
- **Temperature Effect**: -10 degrees
- **Humidity**: Low
- **Visibility**: 80%
- **Movement Speed**: 85%
- **Combat Effects**: Ranged attacks have -15% accuracy; archery unreliable
- **Duration**: 2-5 hours
- **Biomes**: Mountain peaks, cliffs, open plains
- **Special Events**: May trigger rockslides in mountainous terrain

### Fog
- **ID**: fog
- **Temperature Effect**: -5 degrees
- **Humidity**: High
- **Visibility**: 30%
- **Movement Speed**: 75%
- **Combat Effects**: Ranged attacks limited to close range; stealth bonuses apply
- **Duration**: 3-8 hours
- **Biomes**: Coastal areas, swamps, river valleys
- **Special Events**: May hide ambushes; reduces enemy detection range

### Dense Fog
- **ID**: dense_fog
- **Temperature Effect**: -8 degrees
- **Humidity**: High
- **Visibility**: 15%
- **Movement Speed**: 60%
- **Combat Effects**: Melee only beyond 10 feet; +20% stealth bonus for ambushes
- **Duration**: 2-6 hours
- **Biomes**: Swamps, river valleys, coastal areas
- **Special Events**: Navigation difficult; risk of getting lost

### Haze
- **ID**: haze
- **Temperature Effect**: +2 degrees
- **Humidity**: Medium
- **Visibility**: 60%
- **Movement Speed**: 95%
- **Combat Effects**: Ranged attacks have -5% accuracy
- **Duration**: 4-10 hours
- **Biomes**: Urban areas, deserts, volcanic regions
- **Special Events**: May indicate nearby wildfire or volcanic activity

### Humid
- **ID**: humid
- **Temperature Effect**: +5 degrees
- **Humidity**: High
- **Visibility**: 90%
- **Movement Speed**: 90%
- **Combat Effects**: Stamina drains 10% faster
- **Duration**: 6-12 hours
- **Biomes**: Jungles, swamps, coastal areas
- **Special Events**: May trigger heat exhaustion in unprepared characters

### Dry Heat
- **ID**: dry_heat
- **Temperature Effect**: +15 degrees
- **Humidity**: Low
- **Visibility**: 100%
- **Movement Speed**: 85%
- **Combat Effects**: Stamina drains 15% faster; water consumption doubled
- **Duration**: 8-16 hours
- **Biomes**: Deserts, arid plains
- **Special Events**: Risk of dehydration; water sources become critical

### Cold Snap
- **ID**: cold_snap
- **Temperature Effect**: -20 degrees
- **Humidity**: Low
- **Visibility**: 90%
- **Movement Speed**: 80%
- **Combat Effects**: Ice-based attacks deal +25% damage; metal weapons may stick to skin
- **Duration**: 4-12 hours
- **Biomes**: Tundra, mountain peaks, northern regions
- **Special Events**: Water sources freeze; hypothermia risk increases

### Drizzle
- **ID**: drizzle
- **Temperature Effect**: -3 degrees
- **Humidity**: High
- **Visibility**: 70%
- **Movement Speed**: 90%
- **Combat Effects**: Fire-based attacks deal -15% damage; matches and torches extinguish easily
- **Duration**: 2-6 hours
- **Biomes**: All biomes
- **Special Events**: May develop into full rain

---

## Precipitation Conditions

### Light Rain
- **ID**: light_rain
- **Temperature Effect**: -5 degrees
- **Humidity**: High
- **Visibility**: 60%
- **Movement Speed**: 85%
- **Combat Effects**: Fire attacks -20% damage; lightning weapons gain +10% damage
- **Duration**: 2-5 hours
- **Biomes**: All biomes except arid deserts
- **Special Events**: Mud begins to form; tracks become visible

### Moderate Rain
- **ID**: moderate_rain
- **Temperature Effect**: -8 degrees
- **Humidity**: High
- **Visibility**: 45%
- **Movement Speed**: 75%
- **Combat Effects**: Fire attacks -30% damage; ranged accuracy -10%; metal armor conductive
- **Duration**: 3-8 hours
- **Biomes**: All biomes except arid deserts
- **Special Events**: Flooding possible in low areas; rivers rise

### Heavy Rain
- **ID**: heavy_rain
- **Temperature Effect**: -12 degrees
- **Humidity**: High
- **Visibility**: 25%
- **Movement Speed**: 60%
- **Combat Effects**: Fire attacks -50% damage; ranged accuracy -25%; lightning risk +40%
- **Duration**: 2-6 hours
- **Biomes**: All biomes except arid deserts
- **Special Events**: Flash floods possible; visibility severely reduced

### Torrential Rain
- **ID**: torrential_rain
- **Temperature Effect**: -15 degrees
- **Humidity**: High
- **Visibility**: 10%
- **Movement Speed**: 45%
- **Combat Effects**: Fire attacks unusable; ranged attacks nearly impossible; drowning risk
- **Duration**: 1-4 hours
- **Biomes**: Tropical regions, coastal areas
- **Special Events**: Severe flooding; structures may collapse; landslides triggered

### Light Snow
- **ID**: light_snow
- **Temperature Effect**: -10 degrees
- **Humidity**: Medium
- **Visibility**: 65%
- **Movement Speed**: 85%
- **Combat Effects**: Ice attacks +10% damage; fire attacks -10% damage
- **Duration**: 3-8 hours
- **Biomes**: Tundra, mountains, northern regions
- **Special Events**: Snow accumulates; tracks become visible

### Moderate Snow
- **ID**: moderate_snow
- **Temperature Effect**: -15 degrees
- **Humidity**: Medium
- **Visibility**: 45%
- **Movement Speed**: 70%
- **Combat Effects**: Ice attacks +20% damage; fire attacks -20% damage; movement through snow costly
- **Duration**: 4-10 hours
- **Biomes**: Tundra, mountains, northern regions
- **Special Events**: Snow drifts form; paths become blocked

### Heavy Snow
- **ID**: heavy_snow
- **Temperature Effect**: -20 degrees
- **Humidity**: High
- **Visibility**: 25%
- **Movement Speed**: 50%
- **Combat Effects**: Ice attacks +30% damage; fire attacks -30% damage; visibility severely reduced
- **Duration**: 4-12 hours
- **Biomes**: Tundra, mountains, northern regions
- **Special Events**: Avalanche risk; structures may collapse under weight

### Blizzard
- **ID**: blizzard
- **Temperature Effect**: -30 degrees
- **Humidity**: High
- **Visibility**: 5%
- **Movement Speed**: 30%
- **Combat Effects**: All ranged attacks impossible; frostbite damage every 30 minutes; ice attacks +50%
- **Duration**: 4-24 hours
- **Biomes**: Tundra, mountain peaks, northern regions
- **Special Events**: Whiteout conditions; risk of freezing to death; shelter critical

### Ice Storm
- **ID**: ice_storm
- **Temperature Effect**: -25 degrees
- **Humidity**: High
- **Visibility**: 20%
- **Movement Speed**: 40%
- **Combat Effects**: Slipping risk (15% chance per turn); ice damage on exposed skin; metal weapons frozen
- **Duration**: 2-8 hours
- **Biomes**: Mountainous regions, northern areas
- **Special Events**: Ice accumulation weighs down trees; power lines snap; roads impassable

### Sleet
- **ID**: sleet
- **Temperature Effect**: -15 degrees
- **Humidity**: High
- **Visibility**: 40%
- **Movement Speed**: 65%
- **Combat Effects**: Slipping risk (10% chance per turn); fire attacks -25% damage
- **Duration**: 2-6 hours
- **Biomes**: Northern regions, mountainous areas
- **Special Events**: Ice forms on surfaces; travel becomes hazardous

### Freezing Rain
- **ID**: freezing_rain
- **Temperature Effect**: -12 degrees
- **Humidity**: High
- **Visibility**: 35%
- **Movement Speed**: 55%
- **Combat Effects**: Slipping risk (20% chance per turn); ice accumulates on armor and weapons
- **Duration**: 1-4 hours
- **Biomes**: Northern regions, high altitudes
- **Special Events**: Everything coated in ice; travel nearly impossible

### Hail
- **ID**: hail
- **Temperature Effect**: -10 degrees
- **Humidity**: Medium
- **Visibility**: 50%
- **Movement Speed**: 70%
- **Combat Effects**: 10% chance of 1d6 damage per turn if unsheltered; metal armor conducts cold
- **Duration**: 1-3 hours
- **Biomes**: Plains, mountainous areas
- **Special Events**: Hail can damage structures and crops

### Hailstorm
- **ID**: hailstorm
- **Temperature Effect**: -15 degrees
- **Humidity**: Medium
- **Visibility**: 30%
- **Movement Speed**: 55%
- **Combat Effects**: 20% chance of 2d6 damage per turn; ranged attacks impossible; shelter required
- **Duration**: 30 minutes - 2 hours
- **Biomes**: Plains, mountainous areas
- **Special Events**: Severe property damage; livestock at risk

---

## Extreme Conditions

### Thunderstorm
- **ID**: thunderstorm
- **Temperature Effect**: -5 degrees
- **Humidity**: High
- **Visibility**: 35%
- **Movement Speed**: 70%
- **Combat Effects**: Lightning weapons +40% damage; metal armor dangerous (10% lightning strike chance); fire attacks -40%
- **Duration**: 1-4 hours
- **Biomes**: All biomes except arid deserts
- **Special Events**: Lightning strikes may start fires; thunder may cause fear effects

### Severe Thunderstorm
- **ID**: severe_thunderstorm
- **Temperature Effect**: -8 degrees
- **Humidity**: High
- **Visibility**: 20%
- **Movement Speed**: 55%
- **Combat Effects**: Lightning weapons +60% damage; metal armor very dangerous (20% lightning strike chance); fire attacks -60%
- **Duration**: 1-3 hours
- **Biomes**: All biomes except arid deserts
- **Special Events**: Tornadoes may form; large hail; flash flooding

### Electrical Storm
- **ID**: electrical_storm
- **Temperature Effect**: -10 degrees
- **Humidity**: High
- **Visibility**: 25%
- **Movement Speed**: 50%
- **Combat Effects**: Lightning weapons +80% damage; all metal equipment dangerous; magic spells may misfire
- **Duration**: 30 minutes - 2 hours
- **Biomes**: Mountain peaks, volcanic regions
- **Special Events**: Static electricity causes hair to stand; compasses malfunction

### Tornado
- **ID**: tornado
- **Temperature Effect**: -5 degrees
- **Humidity**: High
- **Visibility**: 10%
- **Movement Speed**: 10% (if caught in path)
- **Combat Effects**: All combat impossible; 50% chance of instant death if caught; debris damage
- **Duration**: 10-60 minutes
- **Biomes**: Plains, flat agricultural areas
- **Special Events**: Extreme destruction; structures leveled; trees uprooted

### Dust Devil
- **ID**: dust_devil
- **Temperature Effect**: +5 degrees
- **Humidity**: Low
- **Visibility**: 40%
- **Movement Speed**: 80%
- **Combat Effects**: Ranged accuracy -20%; small objects blown around; sand in eyes
- **Duration**: 5-30 minutes
- **Biomes**: Deserts, dry plains
- **Special Events**: May pick up small items; temporary disorientation

### Sandstorm
- **ID**: sandstorm
- **Temperature Effect**: +10 degrees
- **Humidity**: Low
- **Visibility**: 15%
- **Movement Speed**: 50%
- **Combat Effects**: All ranged attacks impossible; 1d4 sand damage per turn; breathing difficult
- **Duration**: 2-8 hours
- **Biomes**: Deserts, arid regions
- **Special Events**: Navigation impossible; equipment degradation; risk of suffocation

### Haboob
- **ID**: haboob
- **Temperature Effect**: +8 degrees
- **Humidity**: Low
- **Visibility**: 5%
- **Movement Speed**: 40%
- **Combat Effects**: All combat impossible; 2d4 sand damage per turn; suffocation risk
- **Duration**: 30 minutes - 3 hours
- **Biomes**: Deserts, arid regions
- **Special Events**: Complete whiteout; buildings sealed; travel halted

### Volcanic Ash
- **ID**: volcanic_ash
- **Temperature Effect**: +20 degrees
- **Humidity**: Low
- **Visibility**: 30%
- **Movement Speed**: 70%
- **Combat Effects**: Breathing damage (1d6 per hour without mask); fire attacks +20%; water poisoned
- **Duration**: 4-48 hours
- **Biomes**: Volcanic regions
- **Special Events**: Ash fall damages crops; water sources contaminated; respiratory damage

### Ash Storm
- **ID**: ash_storm
- **Temperature Effect**: +25 degrees
- **Humidity**: Low
- **Visibility**: 10%
- **Movement Speed**: 55%
- **Combat Effects**: Breathing damage (2d6 per hour without mask); fire attacks +30%; visibility near zero
- **Duration**: 2-12 hours
- **Biomes**: Volcanic regions
- **Special Events**: Complete environmental hazard; shelter mandatory

### Blizzard (Whiteout)
- **ID**: blizzard_whiteout
- **Temperature Effect**: -35 degrees
- **Humidity**: High
- **Visibility**: 0%
- **Movement Speed**: 20%
- **Combat Effects**: Complete inability to fight; frostbite every 15 minutes; instant death if exposed
- **Duration**: 6-24 hours
- **Biomes**: Arctic regions, extreme northern areas
- **Special Events**: Total isolation; survival depends on shelter; rescue impossible

### Heatwave
- **ID**: heatwave
- **Temperature Effect**: +25 degrees
- **Humidity**: Low
- **Visibility**: 100%
- **Movement Speed**: 75%
- **Combat Effects**: Stamina drains 30% faster; fire attacks +20% damage; dehydration rapid
- **Duration**: 24-72 hours
- **Biomes**: Deserts, tropical regions
- **Special Events**: Water sources dry up; crops wither; heatstroke common

### Tropical Cyclone
- **ID**: tropical_cyclone
- **Temperature Effect**: +5 degrees
- **Humidity**: High
- **Visibility**: 15%
- **Movement Speed**: 30%
- **Combat Effects**: All ranged attacks impossible; structural damage; flooding; projectile debris
- **Duration**: 6-48 hours
- **Biomes**: Coastal tropical regions
- **Special Events**: Storm surge; massive flooding; complete devastation in eye wall

### Monsoon
- **ID**: monsoon
- **Temperature Effect**: -5 degrees
- **Humidity**: High
- **Visibility**: 20%
- **Movement Speed**: 45%
- **Combat Effects**: Fire attacks -50% damage; ranged accuracy -30%; drowning risk
- **Duration**: 12-72 hours
- **Biomes**: Tropical regions, coastal areas
- **Special Events**: Massive flooding; landslides; waterborne diseases spread

### Flash Flood
- **ID**: flash_flood
- **Temperature Effect**: 0 degrees
- **Humidity**: High
- **Visibility**: 25%
- **Movement Speed**: 20%
- **Combat Effects**: Drowning risk (30% per turn if caught); all combat disrupted; debris damage
- **Duration**: 1-6 hours
- **Biomes**: Canyon areas, river valleys, urban environments
- **Special Events**: Complete area inundation; structures swept away; rescue operations needed

### Derecho
- **ID**: derecho
- **Temperature Effect**: -15 degrees
- **Humidity**: High
- **Visibility**: 20%
- **Movement Speed**: 40%
- **Combat Effects**: All ranged attacks impossible; wind damage 3d6 per turn; structures destroyed
- **Duration**: 1-4 hours
- **Biomes**: Plains, agricultural regions
- **Special Events**: Straight-line winds exceed 100mph; widespread destruction

### Firestorm
- **ID**: firestorm
- **Temperature Effect**: +40 degrees
- **Humidity**: Low
- **Visibility**: 15%
- **Movement Speed**: 50%
- **Combat Effects**: Fire attacks +100% damage; all other fire damage doubled; oxygen depleted
- **Duration**: 2-12 hours
- **Biomes**: Forests, grasslands near wildfires
- **Special Events**: Complete combustion of flammable materials; fire tornadoes possible

### Supernova
- **ID**: supernatural_storm
- **Temperature Effect**: Varies wildly (-30 to +30)
- **Humidity**: Varies
- **Visibility**: 0%
- **Movement Speed**: 50%
- **Combat Effects**: All magic amplified; random spell effects; reality distortion
- **Duration**: 1-6 hours
- **Biomes**: Magical regions, ley line intersections
- **Special Events**: Reality tears; planar rifts; magical anomalies

### Static Storm
- **ID**: static_storm
- **Temperature Effect**: -5 degrees
- **Humidity**: Medium
- **Visibility**: 60%
- **Movement Speed**: 90%
- **Combat Effects**: All metal equipment causes 1d4 shock damage per turn; magic spells misfire 25%
- **Duration**: 1-4 hours
- **Biomes**: Crystal caves, magical regions
- **Special Events**: Compasses fail; electronics malfunction; static discharge

### Toxic Rain
- **ID**: toxic_rain
- **Temperature Effect**: -8 degrees
- **Humidity**: High
- **Visibility**: 40%
- **Movement Speed**: 75%
- **Combat Effects**: Poison damage 1d6 per turn if exposed; fire attacks -30% damage
- **Duration**: 2-8 hours
- **Biomes**: Corrupted lands, near magical contamination
- **Special Events**: Water sources poisoned; plant life damaged; environmental hazard

### Lunar Eclipse Storm
- **ID**: lunar_eclipse_storm
- **Temperature Effect**: -15 degrees
- **Humidity**: High
- **Visibility**: 10%
- **Movement Speed**: 60%
- **Combat Effects**: Undead +50% strength; holy magic +30% damage; dark magic +40% damage
- **Duration**: 3-6 hours
- **Biomes**: All biomes during lunar eclipse
- **Special Events**: Undead rise; supernatural creatures active; magical wards weakened

### Solar Flare
- **ID**: solar_flare
- **Temperature Effect**: +30 degrees
- **Humidity**: Low
- **Visibility**: 50% (bright glare)
- **Movement Speed**: 80%
- **Combat Effects**: Fire attacks +50% damage; vision impaired; electronics destroyed
- **Duration**: 1-4 hours
- **Biomes**: All biomes
- **Special Events**: Communication blackout; aurora visible; equipment failure

### Coriolis Storm
- **ID**: coriolis_storm
- **Temperature Effect**: -20 degrees
- **Humidity**: High
- **Visibility**: 5%
- **Movement Speed**: 25%
- **Combat Effects**: All combat impossible; 4d6 cold damage per turn; instant death if caught
- **Duration**: 2-6 hours
- **Biomes**: Polar regions, deep tundra
- **Special Events**: Complete isolation; rescue impossible; survival depends on preparation

### Abyssal Storm
- **ID**: abyssal_storm
- **Temperature Effect**: -40 degrees
- **Humidity**: High
- **Visibility**: 0%
- **Movement Speed**: 15%
- **Combat Effects**: All combat impossible; 6d6 cold damage per turn; sanity loss
- **Duration**: 6-24 hours
- **Biomes**: Deep ocean, underwater regions
- **Special Events**: Pressure changes; deep sea creatures agitated; navigation impossible

### Void Storm
- **ID**: void_storm
- **Temperature Effect**: Absolute zero
- **Humidity**: None
- **Visibility**: 0%
- **Movement Speed**: 0% (time frozen)
- **Combat Effects**: All action impossible; reality distortion; existence threatened
- **Duration**: Unknown
- **Biomes**: Planar boundaries, magical nexuses
- **Special Events**: Reality collapse; dimensional tears; catastrophic magical event
