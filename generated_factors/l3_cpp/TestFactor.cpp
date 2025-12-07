#include "huatai/atsquant/factor/all_factor_types.h"
#include "huatai/atsquant/factor/base_factor.h"
#include "huatai/atsquant/factor/compute.h"
#include "huatai/atsquant/factor/nonfactor/FactorSecOrderBook.h"

namespace huatai::atsquant::factor {

struct FactorTestFactorParam {
    int64_t window = 20;
};
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(FactorTestFactorParam, window)

class FactorTestFactor : public Factor<FactorTestFactorParam> {
    std::shared_ptr<FactorSecOrderBook> nonfac_ob;
    SlidingWindow<double> price_window;

public:
    FACTOR_INIT(FactorTestFactor)
    
    void on_init() override {
        price_window = SlidingWindow<double>{static_cast<size_t>(param().window)};
        nonfac_ob = get_factor<FactorSecOrderBook>();
        if (nonfac_ob == nullptr) {
            throw std::runtime_error("get nonfactor FactorSecOrderBook error!");
        }
    }

    Status calculate() override {
        value() = 0.0;

        if (nonfac_ob->last_px_list.empty()) {
            return Status::OK();
        }

        double last_price = nonfac_ob->last_px_list.back();
        price_window.push(last_price);

        if (price_window.empty()) {
            value() = 0.0;
        } else {
            value() = compute::mean(price_window, price_window.size());
        }

        return Status::OK();
    }
};

FACTOR_REGISTER(FactorTestFactor)

} // namespace huatai::atsquant::factor