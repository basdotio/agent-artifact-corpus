# SR22T Performance Data
# Extracted from Cirrus SR22T POH for use in runway briefing calculations
# Weight: 3600 lb (max gross)
# Data Version: 2023 POH Revision

EMBEDDED_SR22T_PERFORMANCE = {
    "metadata": {
        "aircraft_model": "Cirrus SR22T",
        "weight_lb": 3600,
        "data_source": "Cirrus SR22T POH",
        "data_version": "2023 POH Revision",
        "notes": "Performance data at max gross weight. Reduce distances by ~10% per 100 lb under max gross."
    },
    "v_speeds": {
        # Standard V-speeds for SR22T (Boldmethod methodology)
        "vr_kias": 80,  # Rotation speed - fixed value 77-80 range
        "approach_speeds": {
            "full_flaps": {
                "final_approach_base_kias": 82.5,  # 80-85 KIAS range average
                "threshold_crossing_kias": 79,
                "touchdown_target_kias": 67,  # Just above stall
                "config_notes": "Normal landing configuration"
            },
            "partial_flaps_50": {
                "final_approach_base_kias": 87.5,  # 85-90 KIAS range average
                "threshold_crossing_kias": 84,
                "touchdown_target_kias": 72,
                "config_notes": "Strong crosswind configuration"
            },
            "no_flaps": {
                "final_approach_base_kias": 92.5,  # 90-95 KIAS range average
                "threshold_crossing_kias": 89,
                "touchdown_target_kias": 77,
                "config_notes": "Emergency or high crosswind"
            }
        },
        "wind_corrections": {
            "gust_factor_multiplier": 0.5,  # Add half the gust factor
            "crosswind_partial_flaps_threshold": 15,  # Use 50% flaps for crosswinds > 15kt
            "weight_correction_per_100lb": 1  # Reduce 1kt per 100lb under max gross
        }
    },
    "performance_data": {
        "landing_distance": {
            "conditions": [
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 0,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1117, "total_distance_ft": 2447},
                        "temp_10c": {"ground_roll_ft": 1158, "total_distance_ft": 2505},
                        "temp_20c": {"ground_roll_ft": 1198, "total_distance_ft": 2565},
                        "temp_30c": {"ground_roll_ft": 1239, "total_distance_ft": 2625},
                        "temp_40c": {"ground_roll_ft": 1280, "total_distance_ft": 2685},
                        "temp_50c": {"ground_roll_ft": 1321, "total_distance_ft": 2747}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 1000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1158, "total_distance_ft": 2506},
                        "temp_10c": {"ground_roll_ft": 1200, "total_distance_ft": 2557},
                        "temp_20c": {"ground_roll_ft": 1243, "total_distance_ft": 2630},
                        "temp_30c": {"ground_roll_ft": 1285, "total_distance_ft": 2693},
                        "temp_40c": {"ground_roll_ft": 1327, "total_distance_ft": 2757},
                        "temp_50c": {"ground_roll_ft": 1370, "total_distance_ft": 2821}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 2000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1201, "total_distance_ft": 2568},
                        "temp_10c": {"ground_roll_ft": 1245, "total_distance_ft": 2633},
                        "temp_20c": {"ground_roll_ft": 1289, "total_distance_ft": 2699},
                        "temp_30c": {"ground_roll_ft": 1333, "total_distance_ft": 2765},
                        "temp_40c": {"ground_roll_ft": 1377, "total_distance_ft": 2832},
                        "temp_50c": {"ground_roll_ft": 1421, "total_distance_ft": 2900}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 3000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1246, "total_distance_ft": 2635},
                        "temp_10c": {"ground_roll_ft": 1292, "total_distance_ft": 2702},
                        "temp_20c": {"ground_roll_ft": 1337, "total_distance_ft": 2771},
                        "temp_30c": {"ground_roll_ft": 1383, "total_distance_ft": 2841},
                        "temp_40c": {"ground_roll_ft": 1428, "total_distance_ft": 2911},
                        "temp_50c": {"ground_roll_ft": 1474, "total_distance_ft": 2983}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 4000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1293, "total_distance_ft": 2705},
                        "temp_10c": {"ground_roll_ft": 1340, "total_distance_ft": 2776},
                        "temp_20c": {"ground_roll_ft": 1388, "total_distance_ft": 2848},
                        "temp_30c": {"ground_roll_ft": 1435, "total_distance_ft": 2922},
                        "temp_40c": {"ground_roll_ft": 1482, "total_distance_ft": 2996},
                        "temp_50c": {"ground_roll_ft": 1530, "total_distance_ft": 3070}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 5000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1342, "total_distance_ft": 2779},
                        "temp_10c": {"ground_roll_ft": 1391, "total_distance_ft": 2854},
                        "temp_20c": {"ground_roll_ft": 1440, "total_distance_ft": 2930},
                        "temp_30c": {"ground_roll_ft": 1489, "total_distance_ft": 3007},
                        "temp_40c": {"ground_roll_ft": 1539, "total_distance_ft": 3085},
                        "temp_50c": {"ground_roll_ft": 1588, "total_distance_ft": 3163}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 6000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1393, "total_distance_ft": 2857},
                        "temp_10c": {"ground_roll_ft": 1444, "total_distance_ft": 2936},
                        "temp_20c": {"ground_roll_ft": 1495, "total_distance_ft": 3016},
                        "temp_30c": {"ground_roll_ft": 1546, "total_distance_ft": 3097},
                        "temp_40c": {"ground_roll_ft": 1598, "total_distance_ft": 3179},
                        "temp_50c": {"ground_roll_ft": 1649, "total_distance_ft": 3261}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 8000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1503, "total_distance_ft": 3029},
                        "temp_10c": {"ground_roll_ft": 1558, "total_distance_ft": 3116},
                        "temp_20c": {"ground_roll_ft": 1613, "total_distance_ft": 3205},
                        "temp_30c": {"ground_roll_ft": 1668, "total_distance_ft": 3294},
                        "temp_40c": {"ground_roll_ft": 1724, "total_distance_ft": 3384},
                        "temp_50c": {"ground_roll_ft": 1779, "total_distance_ft": 3475}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 10000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1621, "total_distance_ft": 3221},
                        "temp_10c": {"ground_roll_ft": 1683, "total_distance_ft": 3318},
                        "temp_20c": {"ground_roll_ft": 1743, "total_distance_ft": 3416},
                        "temp_30c": {"ground_roll_ft": 1802, "total_distance_ft": 3515},
                        "temp_40c": {"ground_roll_ft": 1862, "total_distance_ft": 3614},
                        "temp_50c": {"ground_roll_ft": 1921, "total_distance_ft": 3715}
                    }
                }
            ]
        },
        "takeoff_distance": {
            "conditions": [
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 0,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1352, "total_distance_ft": 1865},
                        "temp_10c": {"ground_roll_ft": 1461, "total_distance_ft": 2007},
                        "temp_20c": {"ground_roll_ft": 1574, "total_distance_ft": 2154},
                        "temp_30c": {"ground_roll_ft": 1692, "total_distance_ft": 2307},
                        "temp_40c": {"ground_roll_ft": 1814, "total_distance_ft": 2465},
                        "temp_50c": {"ground_roll_ft": 1941, "total_distance_ft": 2629}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 1000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1443, "total_distance_ft": 1980},
                        "temp_10c": {"ground_roll_ft": 1559, "total_distance_ft": 2131},
                        "temp_20c": {"ground_roll_ft": 1680, "total_distance_ft": 2288},
                        "temp_30c": {"ground_roll_ft": 1805, "total_distance_ft": 2450},
                        "temp_40c": {"ground_roll_ft": 1936, "total_distance_ft": 2618},
                        "temp_50c": {"ground_roll_ft": 2071, "total_distance_ft": 2792}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 2000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1540, "total_distance_ft": 2104},
                        "temp_10c": {"ground_roll_ft": 1664, "total_distance_ft": 2264},
                        "temp_20c": {"ground_roll_ft": 1793, "total_distance_ft": 2431},
                        "temp_30c": {"ground_roll_ft": 1927, "total_distance_ft": 2603},
                        "temp_40c": {"ground_roll_ft": 2066, "total_distance_ft": 2782},
                        "temp_50c": {"ground_roll_ft": 2210, "total_distance_ft": 2967}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 3000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1645, "total_distance_ft": 2236},
                        "temp_10c": {"ground_roll_ft": 1777, "total_distance_ft": 2407},
                        "temp_20c": {"ground_roll_ft": 1914, "total_distance_ft": 2584},
                        "temp_30c": {"ground_roll_ft": 2058, "total_distance_ft": 2767},
                        "temp_40c": {"ground_roll_ft": 2206, "total_distance_ft": 2958},
                        "temp_50c": {"ground_roll_ft": 2361, "total_distance_ft": 3154}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 4000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1757, "total_distance_ft": 2378},
                        "temp_10c": {"ground_roll_ft": 1898, "total_distance_ft": 2559},
                        "temp_20c": {"ground_roll_ft": 2045, "total_distance_ft": 2748},
                        "temp_30c": {"ground_roll_ft": 2198, "total_distance_ft": 2943},
                        "temp_40c": {"ground_roll_ft": 2357, "total_distance_ft": 3146},
                        "temp_50c": {"ground_roll_ft": 2522, "total_distance_ft": 3355}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 5000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 1878, "total_distance_ft": 2530},
                        "temp_10c": {"ground_roll_ft": 2029, "total_distance_ft": 2723},
                        "temp_20c": {"ground_roll_ft": 2186, "total_distance_ft": 2924},
                        "temp_30c": {"ground_roll_ft": 2350, "total_distance_ft": 3132},
                        "temp_40c": {"ground_roll_ft": 2520, "total_distance_ft": 3347},
                        "temp_50c": {"ground_roll_ft": 2696, "total_distance_ft": 3570}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 6000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 2008, "total_distance_ft": 2693},
                        "temp_10c": {"ground_roll_ft": 2170, "total_distance_ft": 2899},
                        "temp_20c": {"ground_roll_ft": 2338, "total_distance_ft": 3113},
                        "temp_30c": {"ground_roll_ft": 2513, "total_distance_ft": 3334},
                        "temp_40c": {"ground_roll_ft": 2694, "total_distance_ft": 3561},
                        "temp_50c": {"ground_roll_ft": 2883, "total_distance_ft": 3800}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 8000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 2300, "total_distance_ft": 3056},
                        "temp_10c": {"ground_roll_ft": 2485, "total_distance_ft": 3290},
                        "temp_20c": {"ground_roll_ft": 2678, "total_distance_ft": 3533},
                        "temp_30c": {"ground_roll_ft": 2878, "total_distance_ft": 3785},
                        "temp_40c": {"ground_roll_ft": 3086, "total_distance_ft": 4046},
                        "temp_50c": {"ground_roll_ft": 3302, "total_distance_ft": 4316}
                    }
                },
                {
                    "weight_lb": 3600,
                    "pressure_altitude_ft": 10000,
                    "performance": {
                        "temp_0c": {"ground_roll_ft": 2640, "total_distance_ft": 3476},
                        "temp_10c": {"ground_roll_ft": 2852, "total_distance_ft": 3730},
                        "temp_20c": {"ground_roll_ft": 3073, "total_distance_ft": 4019},
                        "temp_30c": {"ground_roll_ft": 3303, "total_distance_ft": 4315},
                        "temp_40c": {"ground_roll_ft": 3541, "total_distance_ft": 4603},
                        "temp_50c": {"ground_roll_ft": 3789, "total_distance_ft": 4911}
                    }
                }
            ]
        },
        "takeoff_climb_gradient_91": {
            "climb_speed_kias": 91,
            "weight_lb": 3600,
            "conditions": [
                {
                    "pressure_altitude_ft": 0,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 1020,
                        "temp_0c_ft_per_nm": 879,
                        "temp_20c_ft_per_nm": 752,
                        "temp_40c_ft_per_nm": 634,
                        "temp_50c_ft_per_nm": 579,
                        "temp_isa_ft_per_nm": 782
                    }
                },
                {
                    "pressure_altitude_ft": 2000,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 958,
                        "temp_0c_ft_per_nm": 823,
                        "temp_20c_ft_per_nm": 701,
                        "temp_40c_ft_per_nm": 589,
                        "temp_50c_ft_per_nm": 537,
                        "temp_isa_ft_per_nm": 755
                    }
                },
                {
                    "pressure_altitude_ft": 4000,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 898,
                        "temp_0c_ft_per_nm": 770,
                        "temp_20c_ft_per_nm": 654,
                        "temp_40c_ft_per_nm": 547,
                        "temp_50c_ft_per_nm": 496,
                        "temp_isa_ft_per_nm": 728
                    }
                },
                {
                    "pressure_altitude_ft": 6000,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 841,
                        "temp_0c_ft_per_nm": 719,
                        "temp_20c_ft_per_nm": 608,
                        "temp_40c_ft_per_nm": 506,
                        "temp_50c_ft_per_nm": 458,
                        "temp_isa_ft_per_nm": 702
                    }
                },
                {
                    "pressure_altitude_ft": 8000,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 787,
                        "temp_0c_ft_per_nm": 671,
                        "temp_20c_ft_per_nm": 565,
                        "temp_40c_ft_per_nm": 468,
                        "temp_50c_ft_per_nm": 422,
                        "temp_isa_ft_per_nm": 676
                    }
                },
                {
                    "pressure_altitude_ft": 10000,
                    "performance": {
                        "temp_minus20c_ft_per_nm": 735,
                        "temp_0c_ft_per_nm": 625,
                        "temp_20c_ft_per_nm": 524,
                        "temp_40c_ft_per_nm": 431,
                        "temp_50c_ft_per_nm": 387,
                        "temp_isa_ft_per_nm": 651
                    }
                }
            ]
        },
        "enroute_climb_gradient_120": {
            "climb_speed_kias": 120,
            "weight_lb": 3600,
            "conditions": [
                {
                    "pressure_altitude_ft": 0,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 931,
                        "temp_minus20c_ft_per_nm": 798,
                        "temp_0c_ft_per_nm": 679,
                        "temp_20c_ft_per_nm": 571,
                        "temp_40c_ft_per_nm": 473,
                        "temp_50c_ft_per_nm": 427,
                        "temp_isa_ft_per_nm": 597
                    }
                },
                {
                    "pressure_altitude_ft": 2000,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 866,
                        "temp_minus20c_ft_per_nm": 740,
                        "temp_0c_ft_per_nm": 627,
                        "temp_20c_ft_per_nm": 524,
                        "temp_40c_ft_per_nm": 430,
                        "temp_50c_ft_per_nm": 386,
                        "temp_isa_ft_per_nm": 569
                    }
                },
                {
                    "pressure_altitude_ft": 4000,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 804,
                        "temp_minus20c_ft_per_nm": 685,
                        "temp_0c_ft_per_nm": 577,
                        "temp_20c_ft_per_nm": 480,
                        "temp_40c_ft_per_nm": 390,
                        "temp_50c_ft_per_nm": 349,
                        "temp_isa_ft_per_nm": 542
                    }
                },
                {
                    "pressure_altitude_ft": 6000,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 746,
                        "temp_minus20c_ft_per_nm": 632,
                        "temp_0c_ft_per_nm": 530,
                        "temp_20c_ft_per_nm": 438,
                        "temp_40c_ft_per_nm": 353,
                        "temp_50c_ft_per_nm": 313,
                        "temp_isa_ft_per_nm": 516
                    }
                },
                {
                    "pressure_altitude_ft": 8000,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 690,
                        "temp_minus20c_ft_per_nm": 583,
                        "temp_0c_ft_per_nm": 486,
                        "temp_20c_ft_per_nm": 398,
                        "temp_40c_ft_per_nm": 317,
                        "temp_50c_ft_per_nm": 279,
                        "temp_isa_ft_per_nm": 490
                    }
                },
                {
                    "pressure_altitude_ft": 10000,
                    "performance": {
                        "temp_minus40c_ft_per_nm": 638,
                        "temp_minus20c_ft_per_nm": 536,
                        "temp_0c_ft_per_nm": 444,
                        "temp_20c_ft_per_nm": 360,
                        "temp_40c_ft_per_nm": 284,
                        "temp_50c_ft_per_nm": 248,
                        "temp_isa_ft_per_nm": 466
                    }
                }
            ]
        }
    }
}
