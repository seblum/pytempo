import pandas as pd
import sys
import click


def _save_table(df: pd.DataFrame, file: str, sort: str) -> None:
    filename = f'{file.split(".")[0]}_{sort}.csv'
    df.to_csv(filename, index=True)
    click.echo(
        f"\n{click.style('> Success!',fg='green')} file saved as {filename}")


def _accumulate_hours(df: pd.DataFrame, column_group: list, column_accumulate: str, column_filter: str) -> pd.DataFrame:
    df[column_filter] = pd.to_datetime(
        df[column_filter]) - pd.to_timedelta(7, unit='d')
    column_group_cp = column_group.copy()
    column_group_cp.append(pd.Grouper(key=column_filter, freq='W-MON'))
    df = df.groupby(column_group_cp)[column_accumulate].sum().reset_index().sort_values(column_filter)
    return df


def _convert_hours_to_pd(df: pd.DataFrame, column_hours: str) -> pd.DataFrame:
    df['Person Days'] = (df[column_hours] / 8).round(1)
    df = df.drop(column_hours, axis=1)
    return df

# write output


def _set_output(df: pd.DataFrame, personday: bool) -> tuple[bool, pd.DataFrame]:
    display_column = 'Hours'
    if personday:
        # What do display based on input
        display_column = 'Person Days'
        df = _convert_hours_to_pd(df, 'Hours')
    return display_column, df


@ click.version_option()
@ click.command()
@ click.argument('file')
@ click.option("-s", "--sort", "sort", help="sort by week, month, calendarmonth")
@ click.option("-g", "--group", "group", multiple=True, default=["Username"], help="filter by issue, person")
@ click.option("-pd", "--persondays", "personday", is_flag=True, help="get output in person days")
def main(file: str, sort: str, group, personday: bool) -> None:

    columns = ['Issue Key', 'Work date', 'Username',
               'Project Key', 'Hours', 'Work Description']

    # check whether csv or xcsl and read accordingly
    filetype = f'{file.split(".")[1]}'
    match filetype:
        case 'csv':
            # might be with statement which is better
            input_df = pd.read_csv(file, usecols=columns, sep=",")
            input_df['Work date'] = pd.to_datetime(input_df['Work date'])
        case 'xls' | 'xlsx':
            input_df = pd.read_excel(file, usecols=columns)
            input_df['Work date'] = pd.to_datetime(input_df['Work date'])
        case _:
            click.echo(
                f"{click.style('> I am sorry!', fg='red')} The file format '{filetype}' is currently not supported.")
            quit()

    dataframe = input_df.copy()
    #print(dataframe)

    column_group = list(group)

    # multiple group columns
    click.echo(
        f"{click.style(f'Converting file {file}, sorting by {sort}, grouping by {group}', fg='blue')}\n")
    match sort:
        case "week":

            dataframe = _accumulate_hours(
                df=dataframe, column_group=column_group, column_accumulate='Hours', column_filter='Work date')
            display_column, dataframe = _set_output(dataframe, personday)
            # Pivot table of dataframe
            dataframe = dataframe.pivot(
                index=column_group, columns='Work date')[display_column].fillna(0)
        case "month":
            dataframe['Month'] = dataframe['Work date'].dt.strftime('%m')
            dataframe = dataframe.groupby(column_group)['Hours'].sum(
            ).reset_index().fillna(0)
            _, dataframe = _set_output(dataframe, personday)
            dataframe = dataframe.set_index(column_group)
        case "calendarweek":
            dataframe = _accumulate_hours(
                df=dataframe, column_group=column_group, column_accumulate='Hours', column_filter='Work date')
            # convert week to calendar week
            dataframe['Week number'] = dataframe['Work date'].dt.isocalendar().week
            dataframe = dataframe.drop('Work date', axis=1)
            display_column, dataframe = _set_output(dataframe, personday)
            # Pivot table of dataframe
            dataframe = dataframe.pivot(
                index=column_group, columns='Week number')[display_column].fillna(0)
        case _:
            click.echo(
                f"{click.style('> I am sorry!', fg='red')} '--sort {sort}' is currently not supported.")
            quit()

    click.echo(dataframe)
    _save_table(dataframe, file, sort)
