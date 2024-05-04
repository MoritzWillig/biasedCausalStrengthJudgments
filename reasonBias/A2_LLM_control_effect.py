import matplotlib.pyplot as plt
import pandas as pd

from eval_helpers import process_to_percentage_skip_invalid, model_names_from_responses, \
    to_percentage_histogram, compute_distribution_distance, distribution_distance_names
from excerptor.bundle import Bundle
from reasonBias.base import get_query_path, get_evaluation_path

# Computes the effect of switching from Control to normal queries for LLMs.

datasets = [
    "annealing", #cc_ann, chain_ann
    #"top_k_var",
    "top_p_var",
]

conds = ["cc", "chain"]


def main():
    for metric_name in distribution_distance_names:
        skipped_answers = {}

        eval_data_base_path = get_evaluation_path() / "LLM_control_effect"
        eval_data_path = eval_data_base_path / f"{metric_name}"
        eval_data_path.mkdir(parents=True, exist_ok=True)

        data_dump = {
            "condition_dataset_name": [],
            "condition_cond_name": [],  # cc chain
            "condition_query_name": [],  # alien, econ, sex
            "parameter_value": [],
        }

        for dataset_name in datasets:
            for cond_name in conds:
                print(f"[{dataset_name}] Processing dataset.")

                bundleLLM = Bundle(get_query_path() / f"{cond_name}_{dataset_name}", name=f"{cond_name}_{dataset_name}")
                bundleControl = Bundle(get_query_path() / f"control_{dataset_name}", name=f"control_{dataset_name}")
                for queryLLM, queryControl in zip(bundleLLM.index["queries"], bundleControl.index["queries"]):
                    responsesLLM = bundleLLM.get_all_responses(
                        queryLLM["query_id"],
                        {"_query_name": queryLLM["meta"]["name"]},
                        proccess_func=process_to_percentage_skip_invalid,
                        meta_object=skipped_answers)
                    responsesControl = bundleControl.get_all_responses(
                        queryControl["query_id"],
                        {"_query_name": queryControl["meta"]["name"]},
                        proccess_func=process_to_percentage_skip_invalid,
                        meta_object=skipped_answers)

                    query_name = queryLLM["meta"]["name"]
                    assert queryLLM["meta"]["name"] == queryControl["meta"]["name"]

                    available_models = model_names_from_responses(responsesLLM)

                    full_name = f"{cond_name}_{dataset_name}_{query_name}"

                    plt.figure()

                    for j, model_name in enumerate(available_models):
                        variants = Bundle.get_variants(api_names=model_name, meta=bundleLLM.index["meta"])
                        var_attr = [k for k, v in bundleLLM.index["meta"]["query"].items() if isinstance(v, str)][0]

                        parameter_values = []
                        predicted_values = []

                        for i, variant in enumerate(variants):
                            variant_name = variant["%variant_name"]
                            predictionsLLM = responsesLLM[variant_name]
                            predictionsControl = responsesControl[variant_name]

                            pred_hist_LLM = to_percentage_histogram(predictionsLLM)
                            pred_hist_Control = to_percentage_histogram(predictionsControl)

                            distance_val = compute_distribution_distance(pred_hist_Control, pred_hist_LLM, metric_name=metric_name)
                            parameter_values.append(variant[var_attr])
                            predicted_values.append(distance_val)

                        plt.plot(parameter_values, predicted_values, marker="o", label=model_name)

                        if j == 0:
                            data_dump["condition_dataset_name"].extend([dataset_name] * len(parameter_values))
                            data_dump["condition_cond_name"].extend([cond_name] * len(parameter_values))
                            data_dump["condition_query_name"].extend([query_name] * len(parameter_values))
                            data_dump["parameter_value"].extend(parameter_values)
                        else:
                            pass
                            # FIXME check all parameter_values are equal (org_parameter_values == parameter_values)

                        if model_name not in data_dump:
                            data_dump[model_name] = []
                        data_dump[model_name].extend(predicted_values)

                    plt.legend()
                    plt.savefig(eval_data_path / f"plt_{full_name}.jpg")

        #for k,data_dump in data_dumps.items():
        df = pd.DataFrame.from_dict(data_dump, orient='columns')
        df.to_csv(eval_data_base_path / f"data_{metric_name}.csv", sep=",", index_label="idx")

if __name__ == "__main__":
    main()
