#!/usr/bin/env python3

import argparse

def parse():
    parser = argparse.ArgumentParser(
        description='Extract dG', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--protein',
        help="Path to result_protein.txt",
        required=True)
    parser.add_argument(
        '--water',
        help="Path to result_water.txt",
        required=True)
    parser.add_argument(
        '--output',
        help="Path to result_XXX.csv",
        required=True)
    parser.add_argument(
        '--protein_name',
        help="Name of directory",
        required=True)
    args = parser.parse_args()
    return args

def get_data(filename):
    result = {
    "CGI" : {"dG" : "", "SD" : "" },
    "BAR" : {"dG" : "", "SD" : "" },
    "JARZ" : {"dG" : "", "SD" : "" },
    }
    lines = open(filename).read().split("\n")
    for line in lines:
      if "CGI: dG =" in line:
        result["CGI"]["dG"] = line.split()[3]
      elif "CGI: Std Err (bootstrap) =" in line:
        result["CGI"]["SD"] = line.split()[5]
      elif "BAR: dG =" in line:
        result["BAR"]["dG"] = line.split()[3]
      elif "BAR: Std Err (bootstrap)  =" in line:
        result["BAR"]["SD"] = line.split()[5]
      elif "JARZ: dG Mean    =" in line:
        result["JARZ"]["dG"] = line.split()[4]
      elif "JARZ: Std Err Forward (bootstrap) =" in line:
        result["JARZ"]["SD"] = line.split()[6]
    return result

def build_table(protein_name, protein, water):
    output = ""
    for key in sorted(protein):
      output += f"""{protein_name};{key};{protein[key]["dG"]};{water[key]["dG"]};{protein[key]["SD"]};{water[key]["SD"]}\n"""
    return output
    print(output)

if __name__ == "__main__":
    args = parse()
    protein_data = get_data(args.protein)
    water_data = get_data(args.water)
    open(args.output,"w").write(build_table(args.protein_name, protein_data, water_data))