from aerofiles.igc import Reader

from opensoar.competition.soaringspot import get_info_from_comment_lines


def get_trace(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader(skip_duplicates=True).read(f)

    _, trace = parsed_igc_file['fix_records']

    return trace


def get_task(igc_path):
    with open(igc_path, 'r') as f:
        parsed_igc_file = Reader(skip_duplicates=True).read(f)

    task, contest_information, competitor_information = get_info_from_comment_lines(parsed_igc_file, date=parsed_igc_file["header"][1]["utc_date"])
    return task
