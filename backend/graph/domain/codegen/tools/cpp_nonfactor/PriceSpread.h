#pragma once
#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"

namespace huatai::atsquant::factor {

struct PriceSpreadParam {
  double spread_ratio = 1;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(PriceSpreadParam, spread_ratio)

class PriceSpread : public Factor<PriceSpreadParam> {

public:
  std::vector<double> sample_value;

  FACTOR_INIT(PriceSpread)
  void on_init() override;

  Status calculate() override;
};

FACTOR_REGISTER(PriceSpread)

} // namespace huatai::atsquant::factor