import unittest

from modules.rag_advisor import (
    _build_query,
    _normalize_home,
    _normalize_loan_summary,
    _normalize_prediction,
    _normalize_search_context,
    _normalize_target,
    _normalize_user_profile,
)


class AdvisorContextTest(unittest.TestCase):
    def setUp(self):
        self.profile = _normalize_user_profile(
            {
                "household_type": "신혼부부",
                "purpose": "실거주",
                "available_cash_eok": 3.0,
                "annual_income_man": 8_000,
                "existing_loan_man": 0,
            }
        )
        self.target = _normalize_target(
            {
                "name": "동현",
                "region": "광진구",
                "complex_id": 1,
                "area_serial_no": 1,
                "price_man": 275_000,
                "jeonse_price_man": 70_000,
                "jeonse_ratio_pct": 25.5,
                "area_type": "85㎡이하",
                "supply_area_pyeong": 30.99,
                "exclusive_area_pyeong": 25.68,
                "units": 548,
                "households_by_size": 380,
                "completion": "1985.08",
                "property_type": "아파트",
                "floor_area_ratio": 174.0,
                "building_coverage_ratio": 15.0,
                "monthly_sale_change_pct": -0.9,
                "monthly_jeonse_change_pct": 0.0,
            }
        )
        self.prediction = _normalize_prediction(
            {
                "model_version": "ver16_hierarchical_apt_size_residual",
                "predictions": [
                    self._prediction(12, 29.8, "medium", 8.2),
                    self._prediction(36, 48.8, "low", 10.5),
                    self._prediction(60, 76.0, "low", 10.4),
                ],
            },
            self.target,
        )
        self.loan = _normalize_loan_summary(
            {
                "loan_limit": 20_000,
                "ltv": 7.27,
                "dsr": 15.2,
                "cash_needed": 255_000,
                "asset_gap": -225_000,
                "is_affordable": False,
                "recommended_products": [
                    {
                        "name": "신한 신혼부부/생애주기 우대 주담대",
                        "description": "가구 유형 우대 가능성 확인",
                        "rate": "우대금리 가능",
                        "limit": 20_000,
                    }
                ],
            }
        )
        self.search = _normalize_search_context(
            {
                "region": "광진구",
                "keyword": "동현",
                "price_min_man": 200_000,
                "price_max_man": 300_000,
                "units_min": 500,
                "units_max": 1_000,
                "area_type": "85㎡이하",
                "sort_choice": "AI예측(1년) 높은 순",
            }
        )

    @staticmethod
    def _prediction(months, growth, confidence, p80):
        return {
            "horizon_months": months,
            "predicted_growth_pct": growth,
            "confidence": confidence,
            "prediction_interval_p80": {"half_width_pctp": p80},
            "residual_calibration": {"fallback": "hier_apt_size_id+horizon"},
        }

    def test_all_personalization_fields_are_in_query(self):
        query = _build_query(
            self.profile,
            self.target,
            self.prediction,
            my_info=_normalize_home({}),
            loan_summary=self.loan,
            search_context=self.search,
        )

        required = [
            "가용 자본금: 30,000만원",
            "지역/검색어: 광진구 / 동현",
            "단지명/ID: 동현 / 1",
            "KB 매매/전세시세: 275,000만원 / 70,000만원",
            "12개월: 상승률 +29.8%",
            "36개월: 상승률 +48.8%",
            "60개월: 상승률 +76.0%",
            "필요 자기자금: 255,000만원",
            "가용 자본금 대비 잔여/부족: -225,000만원 (부족)",
            "신한 신혼부부/생애주기 우대 주담대",
        ]
        for text in required:
            self.assertIn(text, query)

    def test_missing_optional_home_is_explicit(self):
        query = _build_query(
            self.profile,
            self.target,
            self.prediction,
            my_info=_normalize_home({}),
            loan_summary=self.loan,
            search_context=self.search,
        )
        self.assertIn("■ 현재 보유 주택\n- 보유 주택: 없음", query)

    def test_available_cash_eok_is_converted_to_manwon(self):
        self.assertEqual(self.profile["available_cash_man"], 30_000)

    def test_missing_numeric_target_fields_are_not_presented_as_zero(self):
        sparse_target = _normalize_target({"name": "정보제한단지"})
        sparse_prediction = _normalize_prediction({}, sparse_target)
        query = _build_query(
            self.profile,
            sparse_target,
            sparse_prediction,
            my_info=_normalize_home({}),
            loan_summary=_normalize_loan_summary({}),
            search_context=_normalize_search_context({}),
        )
        self.assertIn("KB 매매/전세시세: 없음 / 없음", query)
        self.assertIn("전세가율: 없음", query)
        self.assertIn("공급 없음 / 전용 없음", query)
        self.assertIn("세대수: 없음 / 없음", query)


if __name__ == "__main__":
    unittest.main()
