from typing import Any, Dict

# Regional grid carbon intensity (gCO2eq / kWh)
GRID_CARBON_INTENSITY = {
    "us_east_virginia": 370.0,
    "us_west_oregon": 80.0,
    "eu_sweden": 12.0,
    "eu_ireland": 320.0,
    "asia_australia": 680.0,
}

class SustainabilityService:
    @staticmethod
    def estimate_carbon_footprint(
        training_hours: float, 
        gpu_count: int, 
        datacenter_region: str = "us_east_virginia", 
        use_peft: bool = False
    ) -> Dict[str, Any]:
        """Topic 44: Reducing AI environmental impact
        Calculates energy usage and carbon offsets from spatial relocation and model tuning.
        """
        # Average GPU draw: 350 Watts (0.35 kW) per GPU
        gpu_power_kw = 0.35
        # Datacenter cooling overhead (PUE - Power Usage Effectiveness multiplier)
        pue = 1.2
        
        # Power consumed in training run
        total_energy_kwh = training_hours * gpu_count * gpu_power_kw * pue
        
        # Adjust power requirement if PEFT (LoRA/QLoRA) is active (reduces parameter training energy by 90%)
        if use_peft:
            total_energy_kwh *= 0.10
            
        intensity = GRID_CARBON_INTENSITY.get(datacenter_region, 350.0)
        co2_emitted_g = total_energy_kwh * intensity
        co2_emitted_kg = co2_emitted_g / 1000.0
        
        # Recommendations for relocation
        relocation_recommendations = []
        for region, reg_intensity in GRID_CARBON_INTENSITY.items():
            if reg_intensity < intensity:
                saved_g = total_energy_kwh * (intensity - reg_intensity)
                saved_kg = saved_g / 1000.0
                percent = int((intensity - reg_intensity) / intensity * 100)
                relocation_recommendations.append({
                    "target_region": region,
                    "carbon_saving_kg": round(saved_kg, 2),
                    "reduction_percentage": percent
                })
                
        # Sort recommendations by highest savings
        relocation_recommendations.sort(key=lambda x: x["carbon_saving_kg"], reverse=True)
        
        return {
            "training_hours": training_hours,
            "gpu_count": gpu_count,
            "energy_consumed_kwh": round(total_energy_kwh, 2),
            "carbon_intensity_g_kwh": intensity,
            "carbon_emitted_kg": round(co2_emitted_kg, 2),
            "use_peft": use_peft,
            "relocation_options": relocation_recommendations,
            "explanation": (
                f"Carbon footprint estimate: {round(co2_emitted_kg, 2)} kg CO2eq. "
                f"PEFT tuning mode: {'ACTIVE (90% savings)' if use_peft else 'INACTIVE'}."
            )
        }
