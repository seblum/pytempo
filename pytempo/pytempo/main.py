import pandas as pd
import click


def _save_table(df: pd.DataFrame, file: str, sort: str, column_group: list) -> None:
    column_group_string = '_'.join(column_group).replace(' ', '-')
    filename = f'{file.split(".")[0]}_{sort}_{column_group_string}.csv'
    df.to_csv(filename, index=True)
    click.echo(
        f"\n{click.style('> Success!',fg='green')} file saved as {filename}")


def _accumulate_hours(df: pd.DataFrame, column_group: list, column_accumulate: str, column_filter: str) -> pd.DataFrame:
    df[column_filter] = pd.to_datetime(
        df[column_filter]) - pd.to_timedelta(7, unit='d')
    column_group_cp = column_group.copy()
    column_group_cp.append(pd.Grouper(key=column_filter, freq='W-MON'))
    df = df.groupby(column_group_cp)[column_accumulate].sum(
    ).reset_index().sort_values(column_filter)
    return df


def _convert_hours_to_pd(df: pd.DataFrame, column_hours: str) -> pd.DataFrame:
    df['Person Days'] = (df[column_hours] / 8).round(1)
    df = df.drop(column_hours, axis=1)
    return df


def _set_output(df: pd.DataFrame, personday: bool) -> tuple[bool, pd.DataFrame]:
    display_column = 'Hours'
    if personday:
        # What do display based on input
        display_column = 'Person Days'
        df = _convert_hours_to_pd(df, 'Hours')
    return display_column, df


def _check_columns(df_small: list, df_big: list) -> None:
    if not all(elem in df_big.columns for elem in df_small):
        missing_columns = list(set(df_small) - set(df_big.columns))
        click.echo(
            f"{click.style('> I am sorry!', fg='red')} Following columns are not present: {missing_columns}")
        quit()


@ click.version_option()
@ click.command()
@ click.argument('file')
@ click.option("-a", "--accumulate", "accumulate", default="Hours", help="accumulate: Hours")
@ click.option("-d", "--date", "date", default="Work date", help="set the date: Work date")
@ click.option("-s", "--sort", "sort", help="sort by week, month, calendarmonth")
@ click.option("-g", "--group", "group", multiple=True, default=["Username"], help="filter by issue, person")
@ click.option("-pd", "--persondays", "personday", is_flag=True, help="get output in person days")
@ click.option("-c", "--columns", "show_columns", is_flag=True, help="returns all columns")
def main(file: str, accumulate: str, date: str, sort: str, group: tuple, personday: bool, show_columns: bool) -> None:

    if show_columns:
        filetype = f'{file.split(".")[1]}'
        match filetype:
            case 'csv':
                # might be with statement which is better
                input_df = pd.read_csv(file, sep=",")
            case 'xls' | 'xlsx':
                input_df = pd.read_excel(file)
            case _:
                click.echo(
                    f"{click.style('> I am sorry!', fg='red')} The file format '{filetype}' is currently not supported.")
                quit()
        click.echo(
            f"{click.style('> Success!',fg='green')} The file has following columns: {click.style(', '.join(input_df.columns),fg='blue')}")
        quit()

    DATE_COLUMN = date
    ACC_COLUMN = accumulate

    column_group = list(group)  # needs conversion also for later steps
    df_columns = [DATE_COLUMN, ACC_COLUMN] + column_group

    # check whether csv or xcsl and read accordingly
    filetype = f'{file.split(".")[1]}'
    match filetype:
        case 'csv':
            # might be with statement which is better
            dataframe = pd.read_csv(file, sep=",")
            _check_columns(df_small=df_columns, df_big=dataframe)
            dataframe[DATE_COLUMN] = pd.to_datetime(dataframe[DATE_COLUMN])

        case 'xls' | 'xlsx':
            dataframe = pd.read_excel(file)
            _check_columns(df_small=df_columns, df_big=dataframe)
            dataframe[DATE_COLUMN] = pd.to_datetime(dataframe[DATE_COLUMN])
        case _:
            click.echo(
                f"{click.style('> I am sorry!', fg='red')} The file format '{filetype}' is currently not supported.")
            quit()

    # multiple group columns
    click.echo(
        f"{click.style(f'Converting file {file}, sorting by {sort}, grouping by {group}', fg='blue')}\n")
    match sort:
        case "week":

            dataframe = _accumulate_hours(
                df=dataframe, column_group=column_group, column_accumulate=ACC_COLUMN, column_filter=DATE_COLUMN)
            display_column, dataframe = _set_output(dataframe, personday)
            # Pivot table of dataframe
            dataframe = dataframe.pivot(
                index=column_group, columns=DATE_COLUMN)[display_column].fillna(0)
        case "month":
            dataframe['Month'] = dataframe[DATE_COLUMN].dt.strftime('%m')
            dataframe = dataframe.groupby(column_group)[ACC_COLUMN].sum(
            ).reset_index().fillna(0)
            _, dataframe = _set_output(dataframe, personday)
            dataframe = dataframe.set_index(column_group)
        case "calendarweek":
            dataframe = _accumulate_hours(
                df=dataframe, column_group=column_group, column_accumulate=ACC_COLUMN, column_filter=DATE_COLUMN)
            # convert week to calendar week
            dataframe['Week number'] = dataframe[DATE_COLUMN].dt.isocalendar().week
            dataframe = dataframe.drop(DATE_COLUMN, axis=1)
            display_column, dataframe = _set_output(dataframe, personday)
            # Pivot table of dataframe
            dataframe = dataframe.pivot(
                index=column_group, columns='Week number')[display_column].fillna(0)
        case _:
            click.echo(
                f"{click.style('> I am sorry!', fg='red')} '--sort {sort}' is currently not supported.")
            quit()

    click.echo(dataframe)
    _save_table(dataframe, file, sort, column_group)
