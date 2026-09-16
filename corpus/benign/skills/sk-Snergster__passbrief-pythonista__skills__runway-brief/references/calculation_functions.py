# SR22T Runway Brief - Calculation Functions
# All formulas with test cases for validation

import math

def calculate_pressure_altitude(field_elevation_ft, altimeter_inhg):
    """
    Calculate pressure altitude using standard aviation formula.

    Args:
        field_elevation_ft: Airport elevation above MSL
        altimeter_inhg: Current altimeter setting from ATIS/METAR

    Returns:
        Pressure altitude in feet (rounded to nearest 10 ft)

    Formula: PA = Field Elevation + (29.92 - Altimeter) × 1000
    """
    pa = field_elevation_ft + (29.92 - altimeter_inhg) * 1000
    return round(pa / 10) * 10

def test_pressure_altitude():
    """Test cases for pressure altitude"""
    assert calculate_pressure_altitude(0, 29.92) == 0, "Standard day at sea level"
    assert calculate_pressure_altitude(5000, 30.12) == 4800, "High pressure"
    assert calculate_pressure_altitude(5000, 29.72) == 5200, "Low pressure"
    assert calculate_pressure_altitude(5318, 29.85) == 5388, "KSUN typical (rounds to 5390)"
    print("✅ Pressure altitude tests passed")

def calculate_isa_temperature(pressure_altitude_ft):
    """
    Calculate ISA (International Standard Atmosphere) temperature.

    Args:
        pressure_altitude_ft: Pressure altitude

    Returns:
        ISA temperature in Celsius

    Formula: ISA = 15°C - (2°C × altitude_thousands)
    """
    return round(15 - 2 * (pressure_altitude_ft / 1000), 1)

def test_isa_temperature():
    """Test cases for ISA temperature"""
    assert calculate_isa_temperature(0) == 15.0, "Sea level"
    assert calculate_isa_temperature(3000) == 9.0, "3000 ft"
    assert calculate_isa_temperature(5000) == 5.0, "5000 ft"
    print("✅ ISA temperature tests passed")

def calculate_density_altitude(pressure_altitude_ft, actual_temp_c, isa_temp_c):
    """
    Calculate density altitude.

    Args:
        pressure_altitude_ft: Pressure altitude
        actual_temp_c: Actual temperature
        isa_temp_c: ISA temperature at this pressure altitude

    Returns:
        Density altitude in feet (rounded to nearest 50 ft)

    Formula: DA = PA + 120 × (Actual Temp - ISA Temp)
    """
    da = pressure_altitude_ft + (120 * (actual_temp_c - isa_temp_c))
    return round(da / 50) * 50

def test_density_altitude():
    """Test cases for density altitude"""
    # Standard day: actual = ISA, so DA = PA
    assert calculate_density_altitude(5000, 5.0, 5.0) == 5000, "Standard day"

    # Hot day: DA higher than PA
    # At 5000 ft PA, ISA = 5°C, if actual is 25°C (20° above ISA)
    # DA = 5000 + 120×20 = 5000 + 2400 = 7400
    assert calculate_density_altitude(5000, 25.0, 5.0) == 7400, "Hot day"

    # Cold day: DA lower than PA
    assert calculate_density_altitude(5000, -5.0, 5.0) == 3800, "Cold day"
    print("✅ Density altitude tests passed")

def calculate_wind_components(wind_dir_mag, wind_speed_kt, runway_heading_mag):
    """
    Calculate headwind/crosswind components.

    Args:
        wind_dir_mag: Wind direction in degrees magnetic
        wind_speed_kt: Wind speed in knots
        runway_heading_mag: Runway heading in degrees magnetic

    Returns:
        dict with:
            - headwind_kt: Positive = headwind, Negative = tailwind
            - crosswind_kt: Always positive (absolute value)
            - wind_type: "headwind" or "tailwind"

    Note: Headwind/tailwind determined by whether wind angle is
    more aligned with runway direction (headwind) or opposite (tailwind)
    """
    # Calculate angle between wind and runway
    wind_angle = abs(wind_dir_mag - runway_heading_mag)
    if wind_angle > 180:
        wind_angle = 360 - wind_angle

    # Basic components
    headwind_component = wind_speed_kt * math.cos(math.radians(wind_angle))
    crosswind_component = abs(wind_speed_kt * math.sin(math.radians(wind_angle)))

    # Determine if it's actually a headwind or tailwind
    # If wind is coming from 90-270° relative to runway, it's a tailwind
    angle_diff = (wind_dir_mag - runway_heading_mag) % 360
    if 90 < angle_diff < 270:
        headwind_component = -headwind_component  # Make negative for tailwind
        wind_type = "tailwind"
    else:
        wind_type = "headwind"

    return {
        "headwind_kt": round(headwind_component, 1),
        "crosswind_kt": round(crosswind_component, 1),
        "wind_type": wind_type
    }

def test_wind_components():
    """Test cases for wind components"""
    # Direct headwind: Wind 090, Runway 09 (090)
    result = calculate_wind_components(90, 15, 90)
    assert result["headwind_kt"] == 15.0, "Direct headwind"
    assert result["crosswind_kt"] == 0.0, "No crosswind"
    assert result["wind_type"] == "headwind"

    # Direct tailwind: Wind 090, Runway 27 (270)
    result = calculate_wind_components(90, 15, 270)
    assert result["headwind_kt"] == -15.0, "Direct tailwind (negative)"
    assert result["crosswind_kt"] == 0.0, "No crosswind"
    assert result["wind_type"] == "tailwind"

    # 90° crosswind: Wind 180, Runway 09 (090)
    result = calculate_wind_components(180, 15, 90)
    assert abs(result["headwind_kt"]) < 0.1, "No headwind component"
    assert abs(result["crosswind_kt"] - 15.0) < 0.1, "Full crosswind"

    # 45° angle: Wind 135, Runway 09 (090)
    # Headwind = 15 × cos(45°) ≈ 10.6
    # Crosswind = 15 × sin(45°) ≈ 10.6
    result = calculate_wind_components(135, 15, 90)
    assert 10.0 < abs(result["headwind_kt"]) < 11.0, "45° headwind component"
    assert 10.0 < result["crosswind_kt"] < 11.0, "45° crosswind component"

    print("✅ Wind component tests passed")

def assess_density_altitude_impact(density_altitude_ft):
    """
    Assess performance impact based on density altitude.

    Returns:
        str: Impact assessment
    """
    if density_altitude_ft < 2000:
        return "Excellent performance"
    elif density_altitude_ft < 5000:
        return "Good performance, minor reduction"
    elif density_altitude_ft < 8000:
        return "Noticeable performance reduction"
    elif density_altitude_ft < 10000:
        return "Significant performance reduction - caution advised"
    else:
        return "Severe performance degradation - high risk"

def interpolate_performance(conditions_list, pressure_altitude, temperature, value_keys):
    """
    Bilinear interpolation for performance data on pressure altitude AND temperature.

    THIS IS THE ONLY APPROVED INTERPOLATION METHOD.
    DO NOT rewrite this function. DO NOT use linear interpolation.

    Args:
        conditions_list: List of condition dicts from EMBEDDED_SR22T_PERFORMANCE
        pressure_altitude: Pressure altitude in feet
        temperature: Temperature in Celsius
        value_keys: List of keys to extract (e.g., ['ground_roll_ft', 'total_distance_ft'])
                   Or single string for climb gradient data

    Returns:
        dict: Interpolated values for each key, rounded to nearest 50 ft
              OR single value if value_keys is a string (for climb gradients)

    Example:
        takeoff_data = EMBEDDED_SR22T_PERFORMANCE["performance_data"]["takeoff_distance"]["conditions"]
        result = interpolate_performance(takeoff_data, 4500, 25, ['ground_roll_ft', 'total_distance_ft'])
        # Returns: {'ground_roll_ft': 2050, 'total_distance_ft': 3450}
    """
    import math

    # Get all pressure altitudes available
    pa_values = sorted(set(c['pressure_altitude_ft'] for c in conditions_list))

    # Find bounding pressure altitudes
    if pressure_altitude <= pa_values[0]:
        pa_low = pa_high = pa_values[0]
    elif pressure_altitude >= pa_values[-1]:
        pa_low = pa_high = pa_values[-1]
    else:
        for i in range(len(pa_values) - 1):
            if pa_values[i] <= pressure_altitude <= pa_values[i + 1]:
                pa_low = pa_values[i]
                pa_high = pa_values[i + 1]
                break

    # Get temperature keys from first condition's performance data
    first_condition = [c for c in conditions_list if c['pressure_altitude_ft'] == pa_low][0]
    temp_keys = [k for k in first_condition['performance'].keys() if k.startswith('temp_')]

    # Extract temperature values from keys
    temps = []
    for key in temp_keys:
        # Handle formats: temp_0c, temp_20c, temp_minus20c, temp_0c_ft_per_nm, etc.
        temp_str = key.replace('temp_', '').replace('c_ft_per_nm', '').replace('c', '').replace('minus', '-')
        if temp_str and (temp_str[0].isdigit() or temp_str.startswith('-')):
            temps.append(int(temp_str))
    temps.sort()

    # Find bounding temperatures
    if temperature <= temps[0]:
        temp_low = temp_high = temps[0]
    elif temperature >= temps[-1]:
        temp_low = temp_high = temps[-1]
    else:
        for i in range(len(temps) - 1):
            if temps[i] <= temperature <= temps[i + 1]:
                temp_low = temps[i]
                temp_high = temps[i + 1]
                break

    def temp_to_key(t, is_climb_gradient=False):
        """Convert temperature to performance key"""
        if t < 0:
            base = f'temp_minus{abs(t)}c'
        else:
            base = f'temp_{t}c'

        if is_climb_gradient:
            return base + '_ft_per_nm'
        return base

    # Check if this is climb gradient data (has _ft_per_nm suffix)
    is_climb_gradient = '_ft_per_nm' in temp_keys[0]
    single_value = isinstance(value_keys, str)

    def get_value(pa, temp):
        """Get value from conditions list"""
        condition = [c for c in conditions_list if c['pressure_altitude_ft'] == pa][0]
        perf = condition['performance']
        key = temp_to_key(temp, is_climb_gradient)

        if is_climb_gradient or single_value:
            return perf[key]
        else:
            # It's a dict with multiple values
            result = {}
            for vkey in value_keys:
                result[vkey] = perf[key][vkey]
            return result

    # Bilinear interpolation
    if pa_low == pa_high and temp_low == temp_high:
        # Exact match - no interpolation needed
        result = get_value(pa_low, temp_low)
    elif pa_low == pa_high:
        # Interpolate on temperature only
        v1 = get_value(pa_low, temp_low)
        v2 = get_value(pa_low, temp_high)
        t_ratio = (temperature - temp_low) / (temp_high - temp_low)

        if is_climb_gradient or single_value:
            result = v1 + t_ratio * (v2 - v1)
        else:
            result = {}
            for key in value_keys:
                result[key] = v1[key] + t_ratio * (v2[key] - v1[key])
    elif temp_low == temp_high:
        # Interpolate on pressure altitude only
        v1 = get_value(pa_low, temp_low)
        v2 = get_value(pa_high, temp_low)
        pa_ratio = (pressure_altitude - pa_low) / (pa_high - pa_low)

        if is_climb_gradient or single_value:
            result = v1 + pa_ratio * (v2 - v1)
        else:
            result = {}
            for key in value_keys:
                result[key] = v1[key] + pa_ratio * (v2[key] - v1[key])
    else:
        # Full bilinear interpolation
        ll = get_value(pa_low, temp_low)   # Lower-left
        lh = get_value(pa_low, temp_high)  # Lower-right
        hl = get_value(pa_high, temp_low)  # Upper-left
        hh = get_value(pa_high, temp_high) # Upper-right

        pa_ratio = (pressure_altitude - pa_low) / (pa_high - pa_low)
        t_ratio = (temperature - temp_low) / (temp_high - temp_low)

        if is_climb_gradient or single_value:
            # Interpolate on temp first (bottom and top edges)
            bottom = ll + t_ratio * (lh - ll)
            top = hl + t_ratio * (hh - hl)
            # Then interpolate on PA
            result = bottom + pa_ratio * (top - bottom)
        else:
            result = {}
            for key in value_keys:
                # Interpolate on temp first (bottom and top edges)
                bottom = ll[key] + t_ratio * (lh[key] - ll[key])
                top = hl[key] + t_ratio * (hh[key] - hl[key])
                # Then interpolate on PA
                result[key] = bottom + pa_ratio * (top - bottom)

    # Round results to nearest 50 ft (or 10 ft/NM for climb gradients)
    if is_climb_gradient or single_value:
        if is_climb_gradient:
            return round(result / 10) * 10  # Round climb gradients to nearest 10 ft/NM
        else:
            return round(result / 50) * 50
    else:
        for key in result:
            result[key] = round(result[key] / 50) * 50
        return result

def assess_runway_margin(margin_ft, required_ft):
    """
    Assess runway margin safety.

    Args:
        margin_ft: Available - Required
        required_ft: Required distance

    Returns:
        tuple: (category, percentage)
    """
    if required_ft == 0:
        return ("UNKNOWN", 0)

    percentage = (margin_ft / required_ft) * 100

    if percentage >= 50:
        return ("EXCELLENT", int(percentage))
    elif percentage >= 25:
        return ("GOOD", int(percentage))
    elif percentage >= 10:
        return ("ADEQUATE", int(percentage))
    elif percentage >= 0:
        return ("MARGINAL", int(percentage))
    else:
        return ("INSUFFICIENT", int(percentage))

def test_runway_margin():
    """Test cases for runway margin assessment"""
    assert assess_runway_margin(5000, 3000) == ("EXCELLENT", 166)
    assert assess_runway_margin(3000, 2400) == ("GOOD", 25)
    assert assess_runway_margin(2500, 2200) == ("ADEQUATE", 13)
    assert assess_runway_margin(2200, 2100) == ("MARGINAL", 4)
    assert assess_runway_margin(2000, 2100) == ("INSUFFICIENT", -4)
    print("✅ Runway margin tests passed")

def run_all_tests():
    """Run all test cases"""
    print("\n🧪 Running calculation function tests...")
    print("="*50)
    test_pressure_altitude()
    test_isa_temperature()
    test_density_altitude()
    test_wind_components()
    test_runway_margin()
    print("="*50)
    print("✅ All tests passed!\n")

if __name__ == "__main__":
    run_all_tests()
