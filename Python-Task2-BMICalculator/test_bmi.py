import unittest
import bmi_logic as logic

class TestBmiCalculator(unittest.TestCase):
    
    def test_calculate_bmi(self):
        # 70 kg and 1.75 m -> BMI should be 22.86
        bmi = logic.calculate_bmi(70, 1.75)
        self.assertAlmostEqual(bmi, 22.857142857142858)
        
        # Obese check: 100 kg and 1.75 m -> BMI should be 32.65
        bmi_obese = logic.calculate_bmi(100, 1.75)
        self.assertAlmostEqual(bmi_obese, 32.6530612244898)

    def test_calculate_bmi_invalid(self):
        # Check that division by zero or negative heights/weights throws error
        with self.assertRaises(ValueError):
            logic.calculate_bmi(70, 0)
        with self.assertRaises(ValueError):
            logic.calculate_bmi(70, -1.75)
        with self.assertRaises(ValueError):
            logic.calculate_bmi(-70, 1.75)

    def test_category_info(self):
        self.assertEqual(logic.get_category_info(15.0)["category"], "Underweight")
        self.assertEqual(logic.get_category_info(22.0)["category"], "Normal weight")
        self.assertEqual(logic.get_category_info(27.0)["category"], "Overweight")
        self.assertEqual(logic.get_category_info(35.0)["category"], "Obese")

    def test_conversions(self):
        # Test converting 150 lbs, 5 ft, 10 inches to metric
        weight_kg, height_m = logic.convert_imperial_to_metric(150, 5, 10)
        # 150 lbs * 0.45359237 = 68.0388...
        self.assertAlmostEqual(weight_kg, 68.0388555)
        # 70 inches * 0.0254 = 1.778 m
        self.assertAlmostEqual(height_m, 1.778)

        # Test converting back to imperial
        lbs, ft, inches = logic.convert_metric_to_imperial(weight_kg, height_m)
        self.assertAlmostEqual(lbs, 150.0)
        self.assertEqual(ft, 5)
        self.assertAlmostEqual(inches, 10.0)

    def test_validation(self):
        # Valid numerical inputs
        self.assertEqual(logic.validate_numeric("70.5", "weight"), 70.5)
        self.assertEqual(logic.validate_numeric("175", "height"), 175.0)
        
        # Invalid numerical inputs
        with self.assertRaises(ValueError):
            logic.validate_numeric("abc", "weight")
        with self.assertRaises(ValueError):
            logic.validate_numeric("-10", "weight")
        with self.assertRaises(ValueError):
            logic.validate_numeric("0", "height")

if __name__ == "__main__":
    unittest.main()
