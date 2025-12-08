"""
AH Stock Backtest Op
Responsible for backtesting strategy performance:
1. Train model using Ridge regression
2. Calculate IC and RIC
3. Generate stock selection pools (top5)
4. Save intermediate and final backtest results
"""

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import ray
from flowllm.core.context import C
from flowllm.core.op import BaseOp, BaseRayOp
from loguru import logger
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge

from finance_mcp.core.utils import plot_figure

TOP_5 = 5  # Stock pool size (top5)
TOP_10 = 10  # Stock pool size (top10)
BLOCK_SIZE = 10  # Number of blocks (for analyzing return distribution)


@C.register_op()
class AhBacktestTableOp(BaseRayOp):
    """Backtest strategy performance (Parent Op)"""

    def __init__(
            self,
            input_dir: str = "data/feature",
            output_dir: str = "data/backtest",
            max_samples: int = 512,
            use_weekly: bool = False,
            start_date: int = 20200101,
            feature_columns: List[str] = None,
            label_column: str = "a_label",
            label_normalization: Optional[str] = None,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_samples = max_samples
        self.use_weekly = use_weekly
        self.start_date = start_date
        self.feature_columns = feature_columns
        self.label_column = label_column
        self.label_normalization = label_normalization
        # Automatically set file suffix based on use_weekly
        self.file_suffix = "weekly" if use_weekly else "daily"

        # Validate label_normalization parameter
        if label_normalization and label_normalization not in ["mean", "median"]:
            raise ValueError(f"label_normalization must be 'mean', 'median', or None, got '{label_normalization}'")

    def _ensure_output_dir(self) -> None:
        """Ensure output directory exists"""
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_feature_data(self) -> pd.DataFrame:
        """Load feature data"""
        cache_name = "feature_weekly.csv" if self.use_weekly else "feature_daily.csv"
        feature_path = os.path.join(self.input_dir, cache_name)

        if not os.path.exists(feature_path):
            raise FileNotFoundError(
                f"Feature file not found: {feature_path}\n" f"Please run AhFeatureTableOp first to generate features.",
            )

        df = pd.read_csv(feature_path)

        # Remove NaN values
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            logger.warning(f"Dropping {nan_count} NaN values from feature data")
            df = df.dropna()

        logger.info(f"Loaded features: {df.shape} from {feature_path}")
        return df

    def _get_output_filename(self, base_filename: str) -> str:
        """Generate output filename with suffix"""
        if self.file_suffix:
            name, ext = os.path.splitext(base_filename)
            return f"{name}_{self.file_suffix}{ext}"
        return base_filename

    def _save_dataframe(self, df: pd.DataFrame, filename: str) -> None:
        """Save DataFrame to CSV"""
        output_filename = self._get_output_filename(filename)
        output_path = os.path.join(self.output_dir, output_filename)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {output_filename}: {len(df)} rows")

    def _plot_strategies(self, final_df: pd.DataFrame, dates: List[int]) -> None:
        """Plot strategy return curves"""
        strategy_cols = [c for c in final_df.columns if "_uplift" in c]
        if not strategy_cols:
            logger.warning("No strategy columns found for plotting")
            return

        logger.info(f"Plotting {len(strategy_cols)} strategies: {strategy_cols}")
        plot_dict = {col: [v / 100 for v in final_df[col].tolist()] for col in strategy_cols}
        plot_filename = self._get_output_filename("ah_strategy.pdf")
        plot_output = os.path.join(self.output_dir, plot_filename)
        plot_figure(plot_dict, output_path=plot_output, xs=[str(d) for d in dates], ticks_gap=90)
        logger.info(f"Saved strategy plot to {plot_output}")

    def _normalize_labels(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize labels for each day (subtract mean or median)"""
        if not self.label_normalization:
            return feature_df

        logger.info(f"Normalizing labels using {self.label_normalization}")
        feature_df: pd.DataFrame = feature_df.copy()

        # Get all label columns (including a_label and a_label_1d to a_label_5d)
        label_cols = [col for col in feature_df.columns if col.startswith("a_label")]

        for dt in feature_df["dt"].unique():
            dt_mask = feature_df["dt"] == dt

            for label_col in label_cols:
                if label_col not in feature_df.columns:
                    continue

                label_values = feature_df.loc[dt_mask, label_col]

                if self.label_normalization == "mean":
                    baseline = label_values.mean()
                elif self.label_normalization == "median":
                    baseline = label_values.median()
                else:
                    continue

                feature_df.loc[dt_mask, label_col] = label_values - baseline

        logger.info(f"Label normalization completed for {len(label_cols)} label columns")
        return feature_df

    def execute(self) -> None:
        """Execute backtest"""
        self._ensure_output_dir()

        # Load feature data
        feature_df = self._load_feature_data()

        # Normalize labels
        feature_df = self._normalize_labels(feature_df)

        # Set context parameters
        self.context.max_samples = self.max_samples
        self.context.feature_df = feature_df
        self.context.feature_columns = self.feature_columns
        self.context.label_column = self.label_column

        # Get backtest date list
        dt_list = sorted(feature_df.loc[feature_df.a_flag == 1, "dt"].unique())
        self.context.dt_a_list = dt_list
        logger.info(f"Available dates: {dt_list[0]} to {dt_list[-1]} ({len(dt_list)} days)")

        # Filter backtest dates
        backtest_dates = [d for d in dt_list if d >= self.start_date]
        logger.info(f"Backtest dates: {backtest_dates[0]} to {backtest_dates[-1]} ({len(backtest_dates)} days)")

        # Execute backtest in parallel
        backtest_op = self.ops.backtest_op
        result = self.submit_and_join_parallel_op(op=backtest_op, dt=backtest_dates)

        # Organize and save final results
        final_df = pd.DataFrame([r["final"] for r in result]).sort_values("dt")
        self._save_dataframe(final_df, "backtest_final.csv")

        # Organize and save intermediate results (stock pools)
        intermediate_records = [stock for r in result for stock in r["intermediate"]]
        intermediate_df = pd.DataFrame(intermediate_records)
        self._save_dataframe(intermediate_df, "backtest_pools.csv")

        # Print IC/RIC statistics
        for metric in ["model_ic", "model_ric", "rule_ic", "rule_ric"]:
            mean_val = final_df[metric].mean()
            std_val = final_df[metric].std()
            logger.info(f"{metric}: mean={mean_val:.4f}, std={std_val:.4f}")

        # Plot strategy return curves
        self._plot_strategies(final_df, backtest_dates)

        logger.info(f"Backtest completed: {len(backtest_dates)} days, results in {self.output_dir}")


class AhBacktestOp(BaseOp):
    """Single day backtest (Child Op)"""

    @staticmethod
    def _calculate_ic(pred: np.ndarray, actual: np.ndarray) -> Tuple[float, float]:
        """Calculate IC and RIC"""
        try:
            ic, _ = pearsonr(pred, actual)
            ric, _ = spearmanr(pred, actual)
            return ic, ric
        except Exception as e:
            ray.logger.exception(f"Failed to calculate IC: {e}")
            return 0.0, 0.0

    @staticmethod
    def _create_stock_pool_records(
            df: pd.DataFrame,
            dt: int,
            strategy: str,
            pred_col: Optional[str] = None,
    ) -> List[Dict]:
        """Create stock pool records"""
        records = []
        for _, row in df.iterrows():
            records.append(
                {
                    "dt": dt,
                    "strategy": strategy,
                    "name": row["name"],
                    "code": row["code"],
                    "ah_ratio": row["ah_ratio"],
                    "pred_value": row[pred_col] if pred_col else None,
                    "label": row["a_label"],
                    "actual_uplift": row["uplift"],
                }
            )
        return records

    def execute(self) -> Dict:
        dt = self.context.dt
        feature_df = self.context.feature_df
        max_samples = self.context.max_samples

        # Prepare training and test sets
        train_dates = [d for d in self.context.dt_a_list if d < dt][-max_samples:-1]
        train_df = feature_df.loc[feature_df.dt.isin(train_dates)].copy()
        test_df = feature_df.loc[feature_df.dt == dt].copy()

        if test_df.empty:
            ray.logger.warning(f"No test data for dt={dt}")
            return {"final": {}, "intermediate": []}

        # Get feature columns and label column
        feature_cols = self.context.feature_columns
        label_col = self.context.label_column
        pred_col = "pred_y"

        # Prepare data
        train_x = train_df[feature_cols].values
        train_y = train_df[label_col].values
        test_x = test_df[feature_cols].values
        test_y = test_df[label_col].values
        rule_score = test_df["ah_ratio"].values

        # Train Ridge regression model
        model = Ridge(alpha=1.0)
        model.fit(train_x, train_y)

        # Predict
        pred_y = model.predict(test_x)
        test_df[pred_col] = pred_y

        # Calculate IC and RIC
        model_ic, model_ric = self._calculate_ic(pred_y, test_y)
        rule_ic, rule_ric = self._calculate_ic(rule_score, test_y)

        # Generate stock pools (Top 5 and Top 10)
        model_pool_5 = test_df.nlargest(TOP_5, pred_col)
        model_pool_10 = test_df.nlargest(TOP_10, pred_col)
        rule_pool_5 = test_df.nlargest(TOP_5, "ah_ratio")
        rule_pool_10 = test_df.nlargest(TOP_10, "ah_ratio")

        # Build final result (use uplift to calculate actual returns, use label to calculate IC)
        final_result = {
            "dt": dt,
            "size": len(test_df),
            "model_ic": model_ic,
            "model_ric": model_ric,
            "rule_ic": rule_ic,
            "rule_ric": rule_ric,
            # Top5 results
            "model_names": ",".join(model_pool_5["name"].tolist()),
            "model_uplift": model_pool_5["uplift"].mean(),
            "rule_names": ",".join(rule_pool_5["name"].tolist()),
            "rule_uplift": rule_pool_5["uplift"].mean(),
            # Top10 results
            "model_names_10": ",".join(model_pool_10["name"].tolist()),
            "model_uplift_10": model_pool_10["uplift"].mean(),
            "rule_names_10": ",".join(rule_pool_10["name"].tolist()),
            "rule_uplift_10": rule_pool_10["uplift"].mean(),
            # Average of all stocks
            "all_uplift": test_df["uplift"].mean(),
        }

        # Calculate block returns (sort by predicted value, divide into N blocks, use uplift to calculate actual returns)
        block_count = max(1, round(len(test_df) / BLOCK_SIZE))
        test_df_sorted = test_df.sort_values(pred_col, ascending=False)

        for i in range(BLOCK_SIZE):
            start_idx = i * block_count
            end_idx = (i + 1) * block_count
            block_data = test_df_sorted.iloc[start_idx:end_idx]
            final_result[f"p{i}_uplift"] = block_data["uplift"].mean() if len(block_data) > 0 else 0.0

        # Build intermediate results (stock pool details)
        intermediate_result = []
        intermediate_result.extend(self._create_stock_pool_records(model_pool_5, dt, "model_top5", pred_col))
        intermediate_result.extend(self._create_stock_pool_records(rule_pool_5, dt, "rule_top5"))
        intermediate_result.extend(self._create_stock_pool_records(model_pool_10, dt, "model_top10", pred_col))
        intermediate_result.extend(self._create_stock_pool_records(rule_pool_10, dt, "rule_top10"))

        return {"final": final_result, "intermediate": intermediate_result}


def main(
        input_dir: str = "data/feature",
        output_dir: str = "data/backtest",
        max_samples: int = 512,
        use_weekly: bool = False,
        start_date: int = 20200101,
        feature_columns: List[str] = None,
        label_column: str = "a_label",
        label_normalization: Optional[str] = None,
        ray_workers: int = 8,
):
    from finance_mcp import FinanceMcpApp

    with FinanceMcpApp() as app:
        app.service_config.ray_max_workers = ray_workers

        op = AhBacktestTableOp(
            input_dir=input_dir,
            output_dir=output_dir,
            max_samples=max_samples,
            use_weekly=use_weekly,
            start_date=start_date,
            feature_columns=feature_columns,
            label_column=label_column,
            label_normalization=label_normalization,
        )

        op.ops.backtest_op = AhBacktestOp()

        op.call()


if __name__ == "__main__":
    # Daily frequency backtest configuration - default uses 5-day label
    daily_config = {
        "input_dir": "data/feature",
        "output_dir": "data/backtest",
        "max_samples": 512,
        "use_weekly": False,
        "start_date": 20200101,
        "feature_columns": [
            "ah_ratio",
            # "ah_amount",
            # "avg_1d_ah_pct_diff",
            # "avg_5d_ah_pct_diff",
            # "avg_1d_ah_amount_ratio",
            # "avg_5d_ah_amount_ratio",
            "avg_1d_a_pct",
            "avg_1d_hk_pct",
            "avg_5d_a_pct",
            "avg_5d_hk_pct",
            # "avg_20d_a_pct",
            # "avg_20d_hk_pct",
            "avg_1d_a_amount",
            "avg_1d_hk_amount",
            # "avg_5d_a_amount",
            # "avg_5d_hk_amount",
        ],
        "label_column": "a_label_5d",  # Optional: a_label_1d, a_label_2d, a_label_3d, a_label_4d, a_label_5d
        "label_normalization": "mean",  # None / "mean" / "median"
        "ray_workers": 8,
    }

    # Weekly frequency backtest configuration
    weekly_config = {
        "input_dir": "data/feature",
        "output_dir": "data/backtest",
        "max_samples": 512,
        "use_weekly": True,
        "start_date": 20200101,
        "feature_columns": [
            "ah_ratio",
            "ah_amount5",
            "avg_3d_a_pct",
            "avg_3d_hk_pct",
            "avg_10d_a_pct",
            "avg_10d_hk_pct",
        ],
        "label_column": "a_label",  # Weekly frequency uses default label
        "label_normalization": "mean",  # None / "mean" / "median"
        "ray_workers": 8,
    }

    # Execute daily frequency backtest
    main(**daily_config)

    # Execute weekly frequency backtest
    # main(**weekly_config)

    # Example: Backtest using 1-day label
    # daily_1d_config = daily_config.copy()
    # daily_1d_config["label_column"] = "a_label_1d"
    # daily_1d_config["output_dir"] = "data/backtest_1d"
    # main(**daily_1d_config)

    # Example: Backtest using mean normalization
    # daily_mean_config = daily_config.copy()
    # daily_mean_config["label_normalization"] = "mean"
    # daily_mean_config["output_dir"] = "data/backtest_mean"
    # main(**daily_mean_config)

    # Example: Backtest using median normalization
    # daily_median_config = daily_config.copy()
    # daily_median_config["label_normalization"] = "median"
    # daily_median_config["output_dir"] = "data/backtest_median"
    # main(**daily_median_config)
