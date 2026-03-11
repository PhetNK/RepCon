new='Full Path New Config'
old='Full Path Old Config'
des='Full Path Output Report'

if __name__ == "__main__":
    #splite file
    from report_generator import splite_config
    split_old=splite_config(old,default_config=True)
    old_path=split_old.split()
    
    split_new=splite_config(new)
    new_path=split_new.split()

    from report_generator import report_gen
    report = report_gen(old_folder=old_path,new_folder=new_path,des_folder=des)
    report.get_report()  
