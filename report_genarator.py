from datetime import datetime
import pandas as pd
import os
import re

class splite_config:
    def __init__(self,logfile: str="",default_config:bool=False):
        if not logfile: 
            print(f"Not found file !")
            return None
        else: 
            self.logfile = logfile

        file_name=os.path.basename(logfile).split('.')[0]
        if default_config:
            self.des = os.path.join(os.getcwd(),f"temp/{file_name}_old")
        else:
            self.des = os.path.join(os.getcwd(),f"temp/{file_name}_new")
        if not os.path.exists(self.des):
            os.makedirs(self.des)

    def find(self,line:str):  
        key="#" 
        key_start=""
        key_stop=""

        for command in self.check_list:
            if key+command in line.strip():
                key_stop,key_start = line.strip().split("#")
                return True,command,key_start,key_stop
        return False,command,None,None

    def split(self):
        from config import commands
        self.check_list = commands.commands.copy()
        status = False
        buffer = ''
        with open(self.logfile, "r") as f:
            for line in f:
                check_point = line.strip().split("#")
                if not status:
                    status,command,key_start,key_stop = self.find(line)
                if status:
                    buffer += line
                    if len(check_point) != 2:
                        continue
                    if len(check_point) == 2 and check_point[1] != command :
                        filename = command.strip().replace("show ", "").replace(" ", "_") + ".txt"
                        fullname = self.des +"\\"+ filename
                        print(fullname)
                        with open(fullname, "w", encoding="utf-8") as f:
                            f.write(buffer)
                        self.check_list.remove(command)
                        buffer = ''
                        status = False
                        #print(buffer)                    
                        if not self.check_list:
                            break
                        #recheck
                        status,command,key_start,key_stop = self.find(line)
                        if status: buffer = line
        return self.des
    
class report_gen:
    def __init__(self, old_folder: str = "", new_folder: str = "",des_folder:str=''):
        if not os.path.exists(new_folder) or not os.path.exists(old_folder):
            raise FileNotFoundError("Not found the Folder !")
        
        self.old_folder = old_folder
        self.new_folder = new_folder

        self.old_files = set(os.listdir(old_folder))
        self.new_files = set(os.listdir(new_folder))
        self.common_files = sorted(list(self.old_files & self.new_files))

        hostname = os.path.basename(os.path.normpath(self.new_folder))
        date_str = datetime.now().strftime("%d%b%Y_%H-%M-%S")
        
        base_name=f"report_{hostname}_{date_str}.xlsx"
        if des_folder:
            self.rep_output = os.path.join(des_folder,base_name) 
        else:
            self.rep_output =  self.des = os.path.join(os.getcwd(),f"report/{base_name}")
            

    def get_file_diff_df(self, old_file_path, new_file_path):
        if not os.path.exists(old_file_path) or not os.path.exists(new_file_path):
            return pd.DataFrame({'Error': ['File not found']})
            
        def file_to_dict(path):
            data = {}
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    clean_line = line.strip()
                    if not clean_line: continue
                    parts = clean_line.split(maxsplit=1)
                    if len(parts) > 1:
                        data[parts[0]] = parts[1]
                    else:
                        data[parts[0]] = ""
            return data

        old_dict = file_to_dict(old_file_path)
        new_dict = file_to_dict(new_file_path)
        all_keys = sorted(set(old_dict.keys()) | set(new_dict.keys()))

        old_col, new_col, status_col = [], [], []
        for key in all_keys:
            old_val = old_dict.get(key, "Not Present")
            new_val = new_dict.get(key, "Not Present")
            old_full = f"{key} {old_val}" if key in old_dict else ""
            new_full = f"{key} {new_val}" if key in new_dict else ""
            
            old_col.append(old_full)
            new_col.append(new_full)
            status_col.append('Same' if old_val == new_val else 'Changed')
                
        return pd.DataFrame({'Old_Config': old_col, 'New_Config': new_col, 'Status': status_col})
    
    def mlag_report(self, config_file="mlag_interfaces_detail.txt"):
        mlag_path = os.path.join(self.new_folder, config_file)
        if not os.path.exists(mlag_path):
            return None
            
        parsed_data = []
        col_indices = []

        with open(mlag_path, "r", encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            dash_line = ""
            dash_line_idx = -1
            for idx, line in enumerate(lines):
                if line.strip().startswith("----") and " " in line:
                    dash_line = line
                    dash_line_idx = idx
                    break
            
            if not dash_line:
                return None
            
            import re
            for m in re.finditer(r"(-+)", dash_line):
                col_indices.append((m.start(), m.end()))

            for line in lines[dash_line_idx + 1:]:
                if not line.strip() or line.strip().startswith("Total"): 
                    continue

                try:
                    row = {
                        "MLAG":        line[col_indices[0][0]:col_indices[0][1]].strip(),
                        "State":       line[col_indices[1][0]:col_indices[1][1]].strip(),
                        "Local":       line[col_indices[2][0]:col_indices[2][1]].strip(),
                        "Remote":      line[col_indices[3][0]:col_indices[3][1]].strip(),
                        "Oper":        line[col_indices[4][0]:col_indices[4][1]].strip(),
                        "Config":      line[col_indices[5][0]:col_indices[5][1]].strip(),
                        "Last Change": line[col_indices[6][0]:col_indices[6][1]].strip(),
                        "Changes":     line[col_indices[7][0]:col_indices[7][1]].strip()
                    }
                    parsed_data.append(row)
                except IndexError:
                    continue

        return pd.DataFrame(parsed_data) if parsed_data else None

    def get_report(self):
        with pd.ExcelWriter(self.rep_output, engine='xlsxwriter') as writer:
            workbook = writer.book
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})

            for filename in self.common_files:
                                
                old_path = os.path.join(self.old_folder, filename)
                new_path = os.path.join(self.new_folder, filename)

                df = self.get_file_diff_df(old_path, new_path)
                sheet_name = filename.replace('.txt', '')[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:B', 60)
                worksheet.set_column('C:C', 12)

                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                worksheet.conditional_format(1, 0, len(df), 1, {
                    'type': 'formula', 'criteria': '=$C2="Changed"', 'format': red_format
                })

            df_mlag = self.mlag_report()
            if df_mlag is not None:
                sheet_name = "MLAG_Detail"
                df_mlag.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                
                worksheet.set_column('A:F', 12)
                worksheet.set_column('G:G', 30)
                worksheet.set_column('H:H', 10)
                
                for col_num, value in enumerate(df_mlag.columns.values):
                    worksheet.write(0, col_num, value, header_format)

        print(f"Complete to create report: {os.path.basename(self.rep_output)}")
