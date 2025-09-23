"""DataFrame utility functions for Gradio UI components.

This module provides common DataFrame/list operations used across the UI,
eliminating duplicate code for handling Gradio's different data formats.
"""

from typing import Any

import pandas as pd

from cosmos_workflow.utils.logging import logger


def is_dataframe(data: Any) -> bool:
    """Check if data is a pandas DataFrame.

    Args:
        data: Data to check

    Returns:
        True if data is a DataFrame, False otherwise
    """
    return isinstance(data, pd.DataFrame)


def get_selected_ids(data: pd.DataFrame | list, id_column: int = 1) -> list[str]:
    """Get IDs of selected rows (where checkbox in column 0 is True).

    Args:
        data: Gradio table data (DataFrame or list)
        id_column: Column index containing IDs (default: 1)

    Returns:
        List of selected IDs as strings
    """
    selected_ids = []

    if data is None:
        return selected_ids

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            # Get rows where first column (checkbox) is True
            for _, row in data.iterrows():
                if row.iloc[0] is True and len(row) > id_column:
                    selected_ids.append(str(row.iloc[id_column]))
    elif isinstance(data, list):
        # List format
        for row in data:
            if row and len(row) > id_column and row[0] is True:
                selected_ids.append(str(row[id_column]))

    logger.debug("Selected {} items from table", len(selected_ids))
    return selected_ids


def count_selected(data: pd.DataFrame | list) -> int:
    """Count number of selected rows (where checkbox in column 0 is True).

    Args:
        data: Gradio table data (DataFrame or list)

    Returns:
        Number of selected rows
    """
    if data is None:
        return 0

    count = 0

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            # Count rows where first column is True
            count = int(data.iloc[:, 0].sum()) if data.iloc[:, 0].dtype == bool else 0
    elif isinstance(data, list) and len(data) > 0:
        # List format
        count = sum(1 for row in data if row and len(row) > 0 and row[0] is True)

    return count


def select_all(data: pd.DataFrame | list) -> pd.DataFrame | list:
    """Set all checkboxes to True (select all rows).

    Args:
        data: Gradio table data (DataFrame or list)

    Returns:
        Updated data with all rows selected
    """
    if data is None:
        return data

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            # Set first column to True for all rows
            data.iloc[:, 0] = True
    elif isinstance(data, list) and len(data) > 0:
        # List format - update first element of each row
        for row in data:
            if row and len(row) > 0:
                row[0] = True

    return data


def clear_selection(data: pd.DataFrame | list) -> pd.DataFrame | list:
    """Set all checkboxes to False (deselect all rows).

    Args:
        data: Gradio table data (DataFrame or list)

    Returns:
        Updated data with all rows deselected
    """
    if data is None:
        return data

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            # Set first column to False for all rows
            data.iloc[:, 0] = False
    elif isinstance(data, list) and len(data) > 0:
        # List format - update first element of each row
        for row in data:
            if row and len(row) > 0:
                row[0] = False

    return data


def get_row_by_index(data: pd.DataFrame | list, index: int) -> list:
    """Get a specific row by index.

    Args:
        data: Gradio table data (DataFrame or list)
        index: Row index to retrieve

    Returns:
        Row data as a list, or empty list if index is invalid
    """
    if data is None:
        return []

    try:
        if isinstance(data, pd.DataFrame):
            if 0 <= index < len(data):
                return data.iloc[index].tolist()
        elif isinstance(data, list):
            if 0 <= index < len(data):
                return data[index]
    except Exception as e:
        logger.error("Error getting row at index {}: {}", index, str(e))

    return []


def get_cell_value(
    data: pd.DataFrame | list, row_idx: int, col_idx: int, default: Any = None
) -> Any:
    """Get value of a specific cell by row and column index.

    Args:
        data: Gradio table data (DataFrame or list)
        row_idx: Row index
        col_idx: Column index
        default: Default value if cell doesn't exist

    Returns:
        Cell value or default
    """
    if data is None:
        return default

    try:
        if isinstance(data, pd.DataFrame):
            if 0 <= row_idx < len(data) and 0 <= col_idx < len(data.columns):
                return data.iloc[row_idx, col_idx]
        elif isinstance(data, list):
            if 0 <= row_idx < len(data) and 0 <= col_idx < len(data[row_idx]):
                return data[row_idx][col_idx]
    except Exception as e:
        logger.debug("Error getting cell at ({}, {}): {}", row_idx, col_idx, str(e))

    return default


def get_selected_rows(data: pd.DataFrame | list) -> pd.DataFrame | list:
    """Get only the selected rows from the data.

    Args:
        data: Gradio table data (DataFrame or list)

    Returns:
        Subset of data containing only selected rows
    """
    if data is None:
        return data

    if isinstance(data, pd.DataFrame):
        if not data.empty:
            # Return rows where first column is True
            return data[data.iloc[:, 0]]
    elif isinstance(data, list):
        # Return list of rows where first element is True
        return [row for row in data if row and len(row) > 0 and row[0] is True]

    return data


def update_selection_status(
    data: pd.DataFrame | list, row_idx: int, selected: bool
) -> pd.DataFrame | list:
    """Update the selection status of a specific row.

    Args:
        data: Gradio table data (DataFrame or list)
        row_idx: Row index to update
        selected: New selection status

    Returns:
        Updated data
    """
    if data is None:
        return data

    try:
        if isinstance(data, pd.DataFrame):
            if 0 <= row_idx < len(data):
                data.iloc[row_idx, 0] = selected
        elif isinstance(data, list):
            if 0 <= row_idx < len(data) and data[row_idx]:
                data[row_idx][0] = selected
    except Exception as e:
        logger.error("Error updating selection at row {}: {}", row_idx, str(e))

    return data
