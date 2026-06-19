# Salt of the Earth: Quantifying the Impact of Water Salinity on Global Agricultural Productivity

**Authors:** Jason Russ, Esha Zaveri, Richard Damania, Sébastien Desbureaux, Jorge Escurra, Aude-Sophie Rodella
**Source:** World Bank Policy Research Working Paper 9144, Water Global Practice, February 2020
**JEL Classification:** Q10, Q11, Q15, Q25, Q53
**Keywords:** Agriculture, Salinity, Productivity, Food Security, Water Quality

---

## Abstract

Salinity in surface waters is on the rise throughout much of the world. Many factors contribute to this change, including increased water extraction, poor irrigation management, and sea-level rise. To date, no study has attempted to quantify the impacts on global food production. This paper develops a plausibly causal model to test the sensitivity of global and regional agricultural productivity to changes in water salinity. To do so, it utilizes several local and global data sets on water quality and agricultural productivity, and a model that isolates the impact of exogenous changes in water salinity on yields.

The analysis trains a machine-learning model to predict salinity globally, to simulate average global food losses over 2000–13. These losses are found to be high, in the range of the equivalent of 124 trillion kilocalories, or enough to feed more than 170 million people every day, each year. Global maps building on these results show that pockets of high losses occur on all continents, but the losses can be expected to be particularly problematic in regions already experiencing malnutrition challenges.

*This paper is a product of the Water Global Practice, part of a larger effort by the World Bank to provide open access to its research.*

---

## 1. Introduction

Policy discussions surrounding agricultural water use tend to revolve around water scarcity and variability, and their impact on agricultural productivity. While these are indeed critical areas of focus, particularly in the context of climate-change-induced rainfall variability, challenges from water quality constitute an equally important threat that is currently underappreciated. Over-extraction of surface and groundwater, sea-water intrusion, rainfall variability, and poor irrigation water management all contribute to increased salinization of water supplies, with deleterious effects on crop production in many regions.

Although the harm that saline soil and water can have on agricultural productivity is well known and has a long history, no attempt had previously been made to quantify this impact globally. This paper takes advantage of several regional and global data sets on agricultural productivity, land use, and water quality to estimate the average impact of high salinity levels in surface water on crop production.

The analysis begins with regional studies in the Mekong River Basin and river basins of India, where high-quality data exist. Using hydrological models and surface water irrigation data, agricultural productivity is linked to upstream water quality monitoring stations, which indicate the salinity levels flowing onto downstream irrigated fields. By controlling for confounding factors (rainfall, temperature, geographic factors) and carefully accounting for the direction of stream flow, the analysis isolates the impact of plausibly exogenous changes in electrical conductivity (EC) — the most common measure of water salinity — on downstream agricultural yields. The sample is then expanded using monitoring stations from the GEMStat database, covering regions in 36 countries worldwide.

These estimates are used to simulate the average annual fall in yields due to saline water. Impacts on crop production appear even at relatively low salinity levels and rise at a near-linear rate as water salinity increases. Combining a satellite-based measure of agricultural productivity with estimated yield elasticities and globally modeled water salinity data reveals significant annual losses in food production. A simulation of global food losses is performed by training a predictive model of EC at a 0.5-degree grid between 1992 and 2013, combined with the estimated elasticities. Water salinity is estimated to reduce global agricultural production by 124 trillion kilocalories per year — the equivalent annual food budget of 170 million people. These results suggest saline surface and irrigation water represent an underappreciated global food-security concern deserving greater attention.

The relationship between saline water and agricultural production is well known and documented as far back as ancient Sumer (Thompson 2004). Salt interferes with crop growth in several ways: by displacing important nutrients like nitrogen and phosphorus, interfering with photosynthesis and chlorophyll production, withdrawing water from surrounding soil, and increasing plant energy requirements for extracting water from soil (Warrence, Bauder, and Pearson 2002). Crops are not uniformly impacted by salinity — plants with higher Na⁺ and Cl⁻ concentrations in their leaves tend to be more salt-tolerant, as this reduces the amount of salt ions entering plant cells through osmosis (Munns and Gilliham 2015). It has been estimated that approximately 1,125 million hectares of land are salt-affected globally, of which approximately 76 million hectares have been salinized by human-induced activities (Sanower 2019).

### Prior Regional and Crop-Specific Literature

No global study had previously attempted to estimate the impact of salinity on crop production; the existing literature is composed primarily of regional estimates or crop-specific analyses. Recent regional estimates include:

- Dam et al. (2019): in central Vietnam, for each 1% increase in EC levels, paddy rice yields decline by 0.24%.
- Clarke et al. (2015): in coastal Bangladesh, irrigating with saline surface and groundwater will reduce crop yields by at least 25% by the end of the century.
- Dasgupta et al. (2014): rice yields will fall by 15.6% by 2050 in 9 coastal districts in Bangladesh due to climate-induced increases in salinity.
- Genua-Olmedo et al. (2016): in the Ebro Delta, Northeast Spain, rice productivity will fall by up to 50% by 2100 due to sea-level rise effects on soil salinity.

A deep scientific literature also exists on crop-specific salinity sensitivity. Tanji and Kielen (2002) reviewed threshold and slope values for 81 crops in terms of EC. Machado and Serralheiro (2017) reviewed salt tolerance of vegetables, comparing soil and irrigation water salinity tolerance thresholds for 19 common vegetables — finding that vegetables generally tolerate soil salinity below 250 mS/m, with irrigation water tolerances roughly 30–50% lower than soil salinity tolerances. Rameshwaran et al. (2016) found sweet peppers become sensitive to water salinity above 143 mS/m, declining at a rate of 11% thereafter. Arslan et al. (2015) found chickpea, lentil, and fava bean yields fell by 50% when irrigation EC exceeded 420, 440, and 520 mS/m, respectively — suggesting salinity may have an amplified impact on countries whose staple diets rely on more salinity-sensitive crops. While informative, crop-based studies do not indicate the global scale of food production loss due to salinity — the gap this paper addresses.

---

## 2. Data

To estimate the global impact of water salinity on agricultural productivity, several georeferenced data sets on water quality, agricultural yields, land cover, and weather were used.

### 2.1 Water Quality

Electrical conductivity (EC) was used to measure salinity in water. EC measures the ability of an electrical charge to pass through water; distilled or deionized water is a poor conductor, and conductivity improves as dissolved ions (generally dissolved salts) increase. This makes EC a widely used salinity indicator (Miller, Bradford, and Peters 1988), with the added benefit of being easily measured at monitoring stations or with handheld monitors.

e:

- **Mekong River Basin Commission (MRC):** spans Cambodia, Lao PDR, Thailand, and Vietnam. Of 121 stations with EC data, 23 are in Cambodia/Lao PDR, 21 in Thailand, and 54 in Vietnam.
- **Central Water Commission (CWC) of India:** maintains a network of 375 river monitoring stations across nearly all major river basins in India, sampled monthly or quarterly and analyzed at regional laboratories.
- **GEMStat (UN Global Environmental Monitoring System for freshwater):** collected by UNEP and self-reported by participating countries. Contains over 3 million observations across 224 water quality parameters in 71 countries. EC is one of the best-documented parameters, with 167,914 observations across 1,719 stations in 71 countries. Observation frequency varies significantly by station — some have multiple monthly observations, others seasonal or annual (e.g., one Japanese station has 1,721 EC observations alone). All data sets were collapsed to annual station-level observations, producing a panel data set of year/station observations.

### 2.2 Agricultural Productivity and Land Use

Changes in agricultural productivity were measured using a satellite-based estimate of net primary production (NPP), which is linearly related to the solar energy plants absorb over a growing season (Running et al. 2004). Strong positive correlation between satellite-derived NPP and crop yields is well documented (Lobell et al. 2002; Lu and Zhuang 2010; Tum and Günther 2011), making NPP a frequently used yield proxy in economics literature (Strobl and Strobl 2011; Blanc and Strobl 2013, 2014; Zaveri, Russ, and Damania 2019).

Time-varying NPP data come from MODIS (data starting 2000), specifically the annual MOD17A3 measures from 2000–2013 generated by the Numerical Terradynamic Simulation Group (NTSG) at the University of Montana (Zhao et al. 2005), which corrects for cloud contamination prevalent in MODIS land products.

To isolate NPP from cropland specifically (versus natural forests or vegetation), the European Space Agency's (ESA) Climate Change Initiative land cover data set was used — providing 37 land cover classes based on the UN Land Cover Classification System at 300m resolution, derived from reprocessing of four satellite missions (MERIS, SPOT-VGT, AVHRR, PROBA-V). A cross-walking table from Poulter et al. (2015) was used to group classes into a single cropland category.

The final data measures changes in NPP for each 0.1-degree gridcell (~11×11 km at the equator) containing a minimum level of cropland in 2000. The main analysis uses a 30% cropland minimum threshold, with robustness checks at 75% and 90% thresholds — balancing the risk of including non-agricultural gridcells (low threshold) against excessive restriction to only large farming communities (high threshold).

### 2.3 Irrigation Data

Gridcells were restricted to those believed to be irrigated, ensuring the EC measured in surface water reflects the EC reaching crops.

- **India:** irrigation data by district from the Ministry of Agriculture and the International Crops Research Institute for the Semi-Arid Tropics. Only districts where more than 50% of agricultural land is irrigated by surface irrigation were included.
- **Mekong and global analyses:** data from the FAO's Global Map of Irrigated Areas (GMIA) v5.0, providing a global raster of area equipped for irrigation for 2005 at 0.083-degree resolution, aggregated to the 0.1-degree gridcell. GMIA does not distinguish groundwater from surface water irrigation. For the Mekong analysis, this is not a major concern, as surface water irrigation comprises 91% of total irrigation in Thailand, 99% in Lao PDR and Vietnam, and 100% in Cambodia (FAO 2016).

For the global study, ground and surface irrigation cannot be distinguished. However, groundwater and surface water bodies are known to interact — groundwater can be a major, long-term contributor to surface water contamination (Yu et al. 2018; Delsman et al. 2015; De Louw et al. 2010; Holman et al. 2008). In regions exposed to groundwater over-extraction, reduced baseflow contribution can substantially decrease river streamflow (Mukherjee 2018), enhancing salt concentration due to lower dilution capacity. Excessive irrigation can also raise water tables from saline aquifers, causing saline groundwater to seep into freshwater (Mateo-Sagasta et al. 2010).

### 2.4 Weather Data

Weather data come from Matsuura and Willmott (2001) — a gridded data set with monthly precipitation and average temperature observations at 0.5-degree resolution, transformed into average monthly temperature and total annual precipitation (mm) per gridcell.

---

## 3. Empirical Strategy

To determine the impact of saline water on crop productivity, a crop production function is estimated:

```
Δlog(NPPit) = α + λ·g(WQit) + δ·f(climateit) + σi + ρy + θc·Y + εit        (1)
```

where:
- **NPPit** = net primary productivity in gridcell *i* in year *t*
- **g(WQit)** = a measure of water quality
- **f(climateit)** = measures of temperature and rainfall
- **σi** = gridcell fixed effects (time-invariant productivity factors)
- **ρy** = year fixed effects
- **θc · Y** = region-specific time trends (accounting for local economic/political changes)

Several restrictions were placed on the data set for accuracy:

- Only gridcells with at least 30% cropland (per ESA data) are included, with 75% and 90% thresholds tested in robustness checks.
- Agriculture in gridcells must be irrigated (per Section 2.3).
- Gridcells must be no more than 100 km from their matched monitoring station, to ensure water quality at the station reflects irrigation water quality. This threshold balances accuracy (favoring shorter distances) against sample size (favoring longer distances); robustness checks vary this threshold.

To avoid reverse-causality bias — since irrigated agriculture and water extraction can themselves affect downstream water salinity — gridcells were carefully matched to monitoring stations strictly upstream from them.

For the Mekong and India analyses, this used a **hydrological connectivity approach**: streamflow from each gridcell was traced upstream until a monitoring station was found, via (i) delineation of the drainage network, (ii) connecting land areas to the drainage network, (iii) identifying areas impacted by each water quality station following the drainage path, and (iv) computing distances between stations and districts/gridcells.

For the global analysis, given the wide geographic spread of monitoring stations, tracing streamflows directly was infeasible. Instead, gridcells were matched to the nearest monitoring station at a *higher elevation* than the gridcell itself — since water flows only from higher to lower elevations, this still ensures water flows from the station into the gridcell and not the reverse.

---

## 4. Main Results

### Mekong River Basin

A threshold of 100 mS/m (millisiemens per meter) was used to test for impacts — the level at which the Mekong River Commission and other sources estimate impacts on irrigated crops begin (Kongmeng and Larsen 2014; Tanji and Kielen 2002). Results show that when EC exceeds 100 mS/m, agricultural productivity falls by 5.7–8.2%. As cropland requirement restrictions become stricter (30% → 75% → 90%), the point estimate increases slightly but is not highly sensitive to this choice.

### India

Similar to the Mekong region, productivity falls by 5.5–6.6% when EC exceeds the 100 mS/m threshold. This threshold is exceeded by approximately 5% of observations in both India and the Mekong River Basin.

### Global (GEMStat)

Globally, when EC exceeds 100 mS/m, yields decline by 11.0% to 13.5%.

### Flexible (Non-Linear) Model

A more flexible model creates six EC bins, each 40 mS/m wide, with the 0–40 mS/m bin as the comparison group. Results show a nearly linear decline in yields as EC rises. Even in the lowest bin (40–80 mS/m), the yield decline is statistically detectable and significant in magnitude — between 5.2% and 7.4% relative to the omitted bin. This relationship is not sensitive to the cropland threshold used; all point estimates fall within a tight range with overlapping 95% confidence intervals. Across all three samples, non-impacted observations (0–40 mS/m) represent about 50–60% of the sample; the next bin (40–80 mS/m) is about 30%; all subsequent bins are each less than 10%.

---

## 5. Robustness Tests

Two additional sets of checks were performed to corroborate the main results.

### Varying the Distance Threshold

Results were re-estimated using 50 km and 150 km distance thresholds (in addition to the main 100 km threshold) to each upstream monitoring station, for the Mekong, India, and global samples. Changing the distance threshold changes which gridcells are included in the sample (more gridcells as the threshold increases) but does not change which station each gridcell is matched to (gridcells are always matched to their nearest upstream station). Across all regions, the coefficient on EC is not sensitive to changes in the distance threshold, nor are weather control variables, implying the sample changes have little effect on the estimates.

### Varying the EC Threshold

The main results use a 100 mS/m threshold. Alternative thresholds of 75 and 125 mS/m were tested for the Mekong and India regions (the GEMStat data offer enough variation to support the more flexible semi-parametric model in Section 4 directly). In both regions, impacts are found at all thresholds tested, with results scaling monotonically with the threshold used.

---

## 6. Simulating Global Impacts of Water Salinity on Agricultural Production

The results demonstrate the sensitivity of global agricultural production to water salinity. To quantify the magnitude of agricultural losses, a simulation was performed. The GEMStat database, despite wide global coverage, does not cover all agricultural land — notably with large gaps in China and Sub-Saharan Africa, two major agricultural regions where high salinity could be a significant problem.

To fill these gaps, a machine-learning model was trained to predict continuous EC values globally at a 0.5-degree scale, for every year between 1992 and 2013. The approach:

1. Construct a data set covering known drivers of salinity from the scientific literature.
2. Combine EC data from India, the Mekong Basin, and GEMStat for the broadest possible geographic coverage.
3. Randomly split the data into training (80%) and testing (20%) samples.
4. Train a Random Forest algorithm (selected for best fit over linear regressions, support vector machines, and other commonly used algorithms) on the training sample.
5. Choose the best model as the one maximizing the correlation coefficient between observed and predicted values in the testing sample.
6. Use the best model to predict EC for every year between 1992 and 2013, globally, at 0.5-degree resolution.

(Further detail on covariates and estimation procedure is available in Desbureaux et al. 2019.) The correlation coefficient between observed and predicted EC values in the testing sample is **88%**. Where values are poorly predicted, predicted EC tends to be lower than observed EC — meaning the resulting loss estimates can be interpreted as conservative.

Using the flexible-model coefficients (30% cropland threshold), annual NPP changes, and the predicted EC data set, annual agricultural productivity losses due to EC were estimated for each 0.5×0.5-degree gridcell where cropland exceeds 30% of land cover, globally. Resulting NPP losses were converted to kilocalorie equivalents (following Strobl and Strobl 2011; Imhoff et al. 2004).

**Headline result:** Globally, average annual losses from 2001–2013 due to saline water total **124 trillion kilocalorie-equivalents**. Assuming 2,000 calories/person/day, this represents enough food to cover the annual food budgets of **170 million people**.

With the exception of Sub-Saharan Africa (where most food production is rainfed), all continents show large loss hotspots. Very wet regions — the Amazon basin, Southeast Asia, and the southeastern United States — largely avoid salinity-related losses despite being important agricultural zones. Aggregating losses by country shows the impact is generally **not correlated with development level**. The United States has the largest loss of agricultural production — the equivalent of **32 trillion calories per year** — more than double that of Argentina, the country with the next-largest losses.

**Top countries by estimated annual calorie loss (2001–2013, billions of calories/year), approximate ranking:**

United States (~23,500) > Argentina (~9,000) > India (~8,500) > Ukraine (~8,000) > France (~6,000) > Poland (~5,500) > China (~5,000) > Russia (~5,000) > Canada (~4,800) > Spain (~4,700) > Germany (~4,300) > Australia (~4,000) > Romania (~3,500) > Turkey (~3,000) > Mexico (~2,500) > Italy (~2,000) > Hungary (~1,800) > Morocco (~1,700) > Pakistan (~1,500) > Belarus (~1,200)

---

## 7. Conclusions

Addressing water quality needs for agriculture is a tremendous challenge. With agriculture responsible for 70% of freshwater abstractions globally, and an additional 20% increase in water withdrawals needed by 2050 to feed a population of 9 billion, problems of water scarcity often overshadow those of water quality. Nevertheless, this paper's results demonstrate that yield losses due to saline water are significant and deserve far more attention.

There is no one-size-fits-all solution to reducing irrigation water salinity; solutions vary greatly by location and context:

- **Improved irrigation management** can keep salt balance low and steady. Well-designed drainage systems can accomplish this while also preventing waterlogging (also harmful to productivity) — but drainage systems must specifically target the root layer, or they risk removing more salt from the soil than was applied by irrigation, increasing the salt load of water leaving the field and impacting downstream users (Christen, Ayars, and Hornbuckle 2001).
- **Reducing over-extraction** is important, since over-extraction exacerbates salinity through reduced dilution of downstream water. Salt is benign at low concentrations — it is only once concentrations become too high that productivity declines, so removing less water is the simplest way to prevent that threshold being crossed. The link between over-extraction and salinity also creates potential for a vicious cycle, where higher salinity leads to increased extraction, which leads to further increased salinity — an urgency particularly acute for countries already exposed to malnutrition and climate variability, such as in South Asia.
- **Adaptation through crop choice** becomes necessary when reducing water salinity is too difficult or costly. Crops vary widely in salinity tolerance, from large yield declines at relatively low EC to tolerance of EC levels exceeding 1,000 mS/m. The costs and benefits of switching crop varieties relative to other salt-mitigation strategies must be weighed locally to determine the best course of action for both agricultural economic health and food security.

---

## Key References

- Arslan, A., et al. (2016). Evaluating the productivity potential of chickpea, lentil and faba bean under saline water irrigation systems. *Irrigation and Drainage*, 65(1), 19–28.
- Clarke, D., et al. (2015). Projections of on-farm salinity in coastal Bangladesh. *Environmental Science: Processes & Impacts*, 17(6), 1127–1136.
- Dam, T. H. T., et al. (2019). Paddy in saline water: Analysing variety-specific effects of saline water intrusion on the technical efficiency of rice production in Vietnam. *Outlook on Agriculture*.
- Dasgupta, S., et al. (2014). *Climate change, soil salinity, and the economics of high-yield rice production in coastal Bangladesh.* The World Bank.
- Desbureaux, S., et al. (2019). *A Global Assessment of Water Quality Hotspots between 1992 and 2010 for the SDGs.*
- Genua-Olmedo, A., et al. (2016). Sea level rise impacts on rice production: The Ebro Delta as an example. *Science of The Total Environment*, 571, 1200–1210.
- Mukherjee, A., Bhanja, S. N., & Wada, Y. (2018). Groundwater depletion causing reduction of baseflow triggering Ganges river summer drying. *Scientific Reports*, 8, 12049.
- Munns, R., & Gilliham, M. (2015). Salinity tolerance of crops — what is the cost? *New Phytologist*, 208(3), 668–673.
- Running, S. W., et al. (2004). A continuous satellite-derived measure of global terrestrial primary production. *BioScience*, 54(6), 547–560.
- Sanower, H. (2019). Present Scenario of Global Salt Affected Soils, its Management and Importance of Salinity Research. *International Research Journal of Biological Sciences*, 1, 1–3.
- Tanji, K. K., & Kielen, N. C. (2002). *Agricultural Drainage Water Management in Arid and Semi-arid Areas.* FAO.
- Warrence, N. J., Bauder, J. W., & Pearson, K. E. (2002). *Basics of salinity and sodicity effects on soil physical properties.* Montana State University.
- Zhao, M., et al. (2005). Improvements of the MODIS terrestrial gross and net primary production global data set. *Remote Sensing of Environment*, 95(2), 164–176.

*(Full reference list available in the original paper; truncated here for RAG conciseness — ask if the complete bibliography is needed.)*

---

## Tables Summary (for reference)

**Table 1 — Summary statistics across the three regional data sets** (Mekong, India, Global) include: Δlog(NPP), Electrical Conductivity (mS/m), Electrical Conductivity > 100 mS/m (binary), Precipitation (m/year), Temperature (°C), and Distance to monitoring station (km), each with observation counts, means, standard deviations, and min/max ranges.

**Table 2 — Water quality data set comparison:**

| Location | Source | Stations | Years |
|---|---|---|---|
| Mekong River Basin (Cambodia, Lao PDR, Thailand, Vietnam) | Mekong River Basin Commission | 121 | 2000–2013 |
| India | Central Water Commission (CWC) | 425 | 2000–2013 |
| Global (36 countries) | GEMStat | 1,124 | 2000–2013 |

**Tables 3–7** present full regression results (coefficients, standard errors, R² values) for the Mekong, India, and Global samples across varying distance thresholds (50/100/150 km), cropland thresholds (30%/75%/90%), and EC thresholds (75/100/125 mS/m). All confirm the core finding: EC above ~100 mS/m is associated with statistically significant yield declines, robust across specifications.
