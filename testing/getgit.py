import requests
import time
import re


class releasenotes:
    def __init__(self,username,password,branch=False,module="butler_server"):
        self.username = username
        self.password = password
        self.module = module
        self.branch = branch
        self.headers = {'Content-Type': 'application/json'}
        if branch:
            branchURL = branch.replace("/","%2F")
        
            self.url= 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/commits/%s'%(module,branchURL)
        ##?page=4
    def gettopCommit(self,module,branch, github = False):
        if github:
            burl = "https://api.github.com/repos/greyorange/%s/commits/%s"%(module,branch)
            #burl = "https://api.github.com/repos/greyorange/butler_server/commits?per_page=100&sha=8cf15f7e8863145df5a6bd9841d67a7e9ffa77ee"
            ##burl = "https://api.github.com/repos/greyorange/butler_server/commits?per_page=10&sha=e9e3c5403f1b9cdbb1f5f9294fd7365fd6b6a797"
            out = self.getresult(burl)
            #print(out)
            if out:
                return out["sha"]
            else:
                return out
        else:
            branchURL = branch.replace("/","%2F")
            burl= 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/commits/%s'%(module,branchURL)
            out = self.getresult(burl)
            #print(out)
            if out:
                return out["values"][0]["hash"][:7]
            else:
                return out
        
    def fetch_commits_diff(self,repo,sourceRef, destinationRef):
        print("Finding commits for repo '%s' : Commit in %s which are not in %s"%(repo,sourceRef, destinationRef))
        url1 = "https://api.bitbucket.org/2.0/repositories/gorcode/" +\
        repo + "/commits/" + sourceRef + "?exclude=" + destinationRef +\
        "&pagelen=100" +\
        "&fields=values.message,values.hash,values.parents.hash,values.date,values.author.raw,pagelen,next";
        #print(url1)
        main_list = self.fetch_commits_diff_core(url1)
        #print(no_list)
        all_jiras_tmp = [i["jira"] for i in main_list]
        all_jiras = []
        [all_jiras.extend(i) for i in all_jiras_tmp]
        maybe_list = []
        yes_list = []
        no_list = []
        if len(main_list) > 0:
            commonParent = main_list[-1]['parent']
            url2 = "https://api.bitbucket.org/2.0/repositories/gorcode/" +\
            repo + "/commits/" + destinationRef + "?exclude=" + commonParent +\
            "&pagelen=100" +\
            "&fields=values.message,values.hash,values.date,values.author.raw,pagelen,next";
            #print(url2)
            common_commits = self.fetch_commits_diff_core(url2)
        
            common_commits_jira = [i["jira"] for i in common_commits]
            common_commits_jira_list = []
            [common_commits_jira_list.extend(i) for i in common_commits_jira]
            common_commits_commit_list = [i["commit_id"] for i in common_commits]
            common_commits_summary_list = [i["summary"] for i in common_commits]
        for itm1 in main_list:
            if itm1["summary"] in common_commits_summary_list:
                commit_id2 = common_commits_commit_list[common_commits_summary_list.index(itm1["summary"])]
                itm1["commit_id2"] = commit_id2
                yes_list.append(itm1)
            else:
                for jir in itm1["jira"]:
                    if jir in common_commits_jira_list:
                        for jiras in common_commits_jira:
                            if jir in jiras:
                                jir_ind = common_commits_jira.index(jiras)
                                commit_id2 = common_commits_commit_list[jir_ind]
                                itm1["commit_id2"] = commit_id2
                        maybe_list.append(itm1)
                        #print(itm1)
                    else:
                        no_list.append(itm1)
                        
        return no_list,maybe_list,yes_list
       
        
    def fetch_commits_diff_core(self,url):
        
        revertList = []
        outList =[]
        pages = 0;
        pageLimit = 30
        while 1:
            nexturl = False
            out = self.getresult(url)
            print("Accesing Page %d"%pages)
            if out:
                for val in out["values"]:
                    commit = val["hash"][:7]
                    cdate = val["date"]
                    
                    msg = val["message"].splitlines()
                    
                    try:
                        parent = val["parents"][0]["hash"][:7]
                    except:
                        parent = False
                    
                    author = val['author']['raw']
                    summary = msg[0]
                    if summary.find("Commit from Jenkins Job") != -1:
                        continue
                    
                    jiraList = self.getJiras(msg)
                    if len(jiraList) >0:
                        if jiraList[0] == "BSS-3688":
                            print(msg)
                    #if summary.startswith("Revert"):
                        
                        #revertList.extend(jiraList)
                        #print jiraList
                        #continue
            
                    if len(jiraList) > 0:
                        outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate,"parent":parent,"author":author})
                        jiraFound = True
                    else:
                        jiraFound = False  
                    if not jiraFound:
                        jiraFromSummary = re.findall('(?P<a>[bB][sS]{2}-\s*[1-9]{1}[0-9]{3,4})',summary)
                        if len(jiraFromSummary) > 0:
                            jiraList = [j.upper() for j in jiraFromSummary]
                            outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate,"parent":parent,"author":author})
                        else:
                            outList.append({"jira":[],"summary":summary,"commit_id":commit,"date":cdate,"parent":parent,"author":author})
            
            
                if "next" in out.keys():
                    nexturl = out["next"]
                else:
                    nexturl = False
            
            if nexturl:
                url = nexturl
                pages = pages + 1;
                if (pages > pageLimit):
                    msg = "Commits limit reached (" + str(pageLimit*100) + "). Something might be wrong in the logic."
                    print(msg)
                    break
            else: 
                break
        return(outList)
   
    def getresult(self,url):
        r= requests.get(url, auth=(self.username, self.password), headers=self.headers)
        if r.status_code == 200:
            return r.json()
        else:
            return False
        
    def createBranch(self,module,branch, commit, github = False):
        
        if github:
            url = "https://api.github.com/repos/greyorange/%s/git/refs"%(module)
            myheaders = {'Authorization': "Token " + self.password}
            self.body = {"ref": "refs/heads/%s"%branch,"sha": commit}
            r= requests.post(url, headers=myheaders,json=self.body)
        else:
            url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/branches'%self.module
            self.body = {"name" : branch,"target" : {"hash" : commit}}
            r= requests.post(url, auth=(self.username, self.password), headers=self.headers,json=self.body)
        
        if r.status_code == 201:
            return r.json()
        else:
            print(r.status_code,r.json())
            return False
        
    def deleteBranch(self,module,branch, github = False):
        if github:
            url = "https://api.github.com/repos/greyorange/%s/git/refs/heads/%s"%(module,branch)
            myheaders = {'Authorization': "Token " + self.password}
            r= requests.delete(url, headers=myheaders)
        else:
            url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/branches/%s'%(module,branch)
            r= requests.delete(url, auth=(self.username, self.password))
        return r.status_code
        
    def settag(self,module,tagname, commit,github = False):
        if github:
            if tagname[0].isdigit():
                url = "https://api.github.com/repos/greyorange/%s/git/refs"%(module)
                myheaders = {'Authorization': "Token " + self.password}
                self.body = {"ref": "refs/tags/%s"%tagname,"sha": commit}
                r= requests.post(url, headers=myheaders,json=self.body)
            else:
                print(f"{tagname} must start with a number. Please correct.")
                return False
        else:
            if tagname[0].isdigit():
                url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/tags'%module
                self.body = {"name" : tagname,"target" : {"hash" : commit}}
            else:
                print(f"{tagname} must start with a number. Please correct.")
                return False
            r= requests.post(url, auth=(self.username, self.password), headers=self.headers,json=self.body)
        if r.status_code == 201:
            return r.json()
        else:
            return False
        
    def deleteTag(self,module, tag,github = False):
        if github:
            url = "https://api.github.com/repos/greyorange/%s/git/refs/tags/%s"%(module,tag)
            myheaders = {'Authorization': "Token " + self.password}
            r= requests.delete(url, headers=myheaders)
            print(r.content)
        else:
            url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/tags/%s'%(module,tag)
            r= requests.delete(url, auth=(self.username, self.password))
        return r.status_code
        
    def getAllTags(self):
        url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/tags'%(self.module)
        r= requests.get(url, auth=(self.username, self.password))
        
        if r.status_code == 200:
            data = r.json()
            print(data)
          
        else:
            return []
        
    def getTag(self,module,tag,github = False):
        if github:
            
            url = "https://api.github.com/repos/greyorange/%s/commits/%s"%(module,tag)
            myheaders = {'Authorization': "Token " + self.password}
            r= requests.get(url, headers=myheaders)
            return r.json()["sha"]
        else:
            url = 'https://api.bitbucket.org/2.0/repositories/gorcode/%s/refs/tags/%s'%(module,tag)
            r= requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            data = r.json()
            msg = data["target"]["message"].splitlines()
            jiraList = self.getJiras(msg)
            return data["target"]["hash"][:7],data["target"]['date'],jiraList
        else:
            return False
      
    def getJiras(self,msg):  
        ###re.findall("BSS\s*-\s*\d{4,5}",m)
        jiraList = []
        jira_found = False
        for m in msg:
            #print(m)
            if m.find("JIRA Issues") != -1:
                
                jira=  m.split(":")[1].strip()
                jiraList = [j.strip() for j in jira.split(",")]
                jiraList = [j.upper() for j in jiraList]
                jiraList = [j for j in jiraList if len(j)>8]
                if len(jiraList) == 0:
                    jira_found = False
                else:
                    jira_found =True
        if not jira_found:
            
            for m in msg:
                tmpList = []
                out=  re.findall("BSS\s*-\s*[1-9]{1}[0-9]{4}",m)
                #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
                
                for i in out:
                    tmpList.append("".join(i.split(" ")))
                    
                out2=  re.findall("PATA\s*-\s*[1-9]{1}[0-9]{2,4}",m)
                #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
                
                for i in out2:
                    tmpList.append("".join(i.split(" ")))
                    
                out3=  re.findall("GM\s*-\s*[1-9]{1}[0-9]{2,5}",m)
                #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
                
                for i in out3:
                    tmpList.append("".join(i.split(" ")))
                jiraList.extend(tmpList)
        jiraList = list(set(jiraList))
        #print(jiraList)
        return jiraList
    
    def getJirasGithub(self,msg):  
        ###re.findall("BSS\s*-\s*\d{4,5}",m)
        jiraList = []
        jira_found = False
        
        tmpList = []
        out=  re.findall("BSS\s*-\s*[1-9]{1}[0-9]{4}",msg)
        #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
        
        for i in out:
            tmpList.append("".join(i.split(" ")))
            
        out2=  re.findall("PATA\s*-\s*[1-9]{1}[0-9]{2,4}",msg)
        #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
        
        for i in out2:
            tmpList.append("".join(i.split(" ")))
        
            
        out3=  re.findall("GM\s*-\s*[1-9]{1}[0-9]{2,5}",msg)
        #out=  re.findall("BSS\s*-\s*\d{4,5}",m)
        
        for i in out3:
            tmpList.append("".join(i.split(" ")))
        jiraList.extend(tmpList)
        jiraList = list(set(jiraList))
        #print(jiraList)
        return jiraList
    
    def getPreviousTag(self,tag):
        lastDig = int(tag.split(".")[2])-1
        #print(lastDig)
        if lastDig <0:
            return False
        tTag = tag.split(".")[:-1]
        tTag.append(str(lastDig))
        pTag = ".".join(tTag)
        return self.getTag(pTag)
    
    def getPreviousTag2(self,tag):
        
        return self.getTag("4.8.6.2")
        
    def gitoutputcommit(self,url,startCommit,endCommit):
        startParsing = False
        outList =[]
        out = self.getresult(url)
        for val in out["values"]:
            commit = val["hash"][:7]
            if endCommit == commit:
                startParsing =True
            if startParsing:
                if startCommit == commit:
                    break
                msg = val["message"].splitlines()
                summary = msg[0]
                print(summary)
                if summary.find("Merge branch") != -1:
                    continue
                cdate = val["date"].split("T")[0]
                jiraList = self.getJiras(msg)

                if len(jiraList) > 0:
                    outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                    jiraFound = True
                else:
                    jiraFound = False
                      
                if not jiraFound:
                    outList.append({"jira":[],"summary":summary,"commit_id":commit,"date":cdate})
        return outList
    
    def parseOutCommit(self,url,startCommit,endCommit,startParsing,startFound,outList,currentPage):
        #print(url,startCommit,endCommit,startParsing,startFound,outList,currentPage)
        out = self.getresult(url)
        #print(out)
        revertList = []
        #try:
        if out:
            for val in out["values"]:
                commit = val["hash"][:7]
                ##print(commit)
                cdate = val["date"]
                if commit == endCommit:
                    print("Endcommit",commit)
                    startParsing =True
                if startParsing:
                     
                    msg = val["message"].splitlines()
                    summary = msg[0]
                    if summary.find("Commit from Jenkins Job") != -1:
                        if commit == startCommit:
                            print("startcommit",commit)
                            #print startDate ,cdate
                            startFound =True
                            break
                        continue
                    
                    jiraList = self.getJiras(msg)
                    if summary.startswith("Revert"):
                        if commit == startCommit:
                            print("startcommit",commit)
                            #print startDate ,cdate
                            startFound =True
                            break
                        #print val
                        revertList.extend(jiraList)
                        #print jiraList
                        continue
            
                    if len(jiraList) > 0:
                        outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                        jiraFound = True
                    else:
                        jiraFound = False  
                    if not jiraFound:
                        jiraFromSummary = re.findall('(?P<a>[bB][sS]{2}-\s*[1-9]{1}[0-9]{3,4})',summary)
                        if len(jiraFromSummary) > 0:
                            jiraList = [j.upper() for j in jiraFromSummary]
                            outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                        else:
                            outList.append({"jira":[],"summary":summary,"commit_id":commit,"date":cdate})
                    if commit == startCommit:
                        print("startcommit",commit)
                        #print startDate ,cdate
                        startFound =True
                        break
            #currentPage
            if (not startParsing) and startFound:
                page = out['next'].split("?")[1]
                print("endCommit %s trying on %s "%(endCommit,page))
                url = self.url+"?"+page
                currentPage += 1
                self.parseOutCommit(url, startCommit, endCommit, startParsing,startFound, outList,currentPage)
                 
            if (not startFound) and startParsing:
                page = out['next'].split("?")[1]
                print("startcommit %s trying on %s "%(startCommit,page))
                url = self.url+"?"+page
                currentPage += 1
                self.parseOutCommit(url, startCommit, endCommit, startParsing,startFound, outList,currentPage)
                
                 
            if (not startFound) and (not startParsing):
                page = out['next'].split("?")[1]
                print("endCommit %s trying on %s "%(endCommit,page))
                url = self.url+"?"+page
                currentPage += 1
                self.parseOutCommit(url, startCommit, endCommit, startParsing,startFound, outList,currentPage)
                 
            #print outList
             
            for o in outList:
                for ojira in o["jira"]:
                    if ojira in revertList:
                        if o in outList:
                            outList.remove(o)
            noChangeTag =[]
    
            if len(outList)> 0:
                return outList,outList[0]['commit_id'],noChangeTag
            else:
                return outList,False,noChangeTag
        #except:
        else:
            return [],False,False
#         
    def parseOut(self,url,startDate,endDate,startParsing,startFound,outList,currentPage,raw=False):
        out = self.getresult(url)
        ##print(out)
        revertList = []
        #try:
        if out:
            for val in out["values"]:
                commit = val["hash"][:7]
                
                cdate = val["date"]#.split("T")[0]
                if endDate >= cdate:
                    startParsing =True
                if startParsing:
                    ##print(commit)
                    msg = val["message"].splitlines()
                    summary = msg[0]
                    if summary.find("Commit from Jenkins Job") != -1:
                        continue
                    
                    
                    jiraList = self.getJiras(msg)
                    if not raw:
                        if summary.startswith("Revert"):
                            #print val
                            revertList.extend(jiraList)
                            #print jiraList
                            continue
    
                    if len(jiraList) > 0:
                        outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                        jiraFound = True
                    else:
                        jiraFound = False  
                    if not jiraFound:
                        jiraFromSummary = re.findall('(?P<a>[bB][sS]{2}-\s*[1-9]{1}[0-9]{3,4})',summary)
                        if len(jiraFromSummary) > 0:
                            jiraList = [j.upper() for j in jiraFromSummary]
                            outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                        else:
                            outList.append({"jira":[],"summary":summary,"commit_id":commit,"date":cdate})
                    if startDate >= cdate:
                        print(startDate ,cdate)
                        startFound =True
                        break
            #currentPage
            if (not startParsing) and startFound:
                page = out['next'].split("?")[1]
                print("Endate %s trying on %s "%(endDate,page))
                url = self.url+"?"+page
                self.parseOut(url, startDate, endDate, startParsing,startFound, outList,currentPage,raw)
                
            if (not startFound) and startParsing:
                page = out['next'].split("?")[1]
                print("Startdate %s trying on %s "%(startDate,page))
                url = self.url+"?"+page
                self.parseOut(url, startDate, endDate, startParsing,startFound, outList,currentPage,raw)
                
            if (not startFound) and (not startParsing):
                page = out['next'].split("?")[1]
                print("Endate %s trying on %s "%(endDate,page))
                url = self.url+"?"+page
                self.parseOut(url, startDate, endDate, startParsing,startFound, outList,currentPage,raw)
            if not raw:
                for o in outList:
                    for ojira in o["jira"]:
                        if ojira in revertList:
                            try:
                                outList.remove(o)
                            except:
                                pass
            noChangeTag =[]
            for o in outList:
                try:
                    print(o['commit_id'],o["jira"][0], end=' ')
                except:
                    print(o['commit_id'], end=' ')
                if not self.isExistinInterval(startDate,endDate,o['date']):
                    noChangeTag.append(o['commit_id'])
                    outList.remove(o)
            print(outList)
            if len(outList)> 0:
                return outList,outList[0]['commit_id'],noChangeTag
            else:
                return outList,False,noChangeTag
        # except:
        else:
            return [],False,False
   
    def isExistinInterval(self,startTime, endTime,gitTime):
       
        try:
            stTime =time.mktime(time.strptime(startTime, "%Y-%m-%dT%H:%M:%S"))
        except:
            startTime = startTime.split("+")[0]
            #startTime = ":".join(startTime.split(":")[:-1])
            #print startTime
            stTime =time.mktime(time.strptime(startTime, "%Y-%m-%dT%H:%M:%S"))
        enTime = time.mktime(time.strptime(endTime, "%Y-%m-%dT%H:%M:%S"))
        try:
            gTime = time.mktime(time.strptime(gitTime, "%Y-%m-%dT%H:%M:%S"))
        except:
            gitTime = gitTime.split("+")[0]
            #gitTime = ":".join(gitTime.split(":")[:-1])
            gTime = time.mktime(time.strptime(gitTime, "%Y-%m-%dT%H:%M:%S"))
        if gTime < enTime and gTime >stTime:
            print(startTime,gitTime, endTime, "true")
            return True
        else:
            print(startTime,gitTime, endTime, "false")
            return False
        
    def gitoutputdate(self,startDate,endDate,raw=False,github = False):
        print(startDate,endDate)
        if startDate <= endDate:
            ##2022-06-07T13:49:30Z
            try:
                dd = time.mktime(time.strptime(startDate.split("+")[0], "%Y-%m-%dT%H:%M:%S.%f"))
            except:
                try:
                    dd = time.mktime(time.strptime(startDate.split("+")[0], "%Y-%m-%dT%H:%M:%S"))
                except:
                    dd = time.mktime(time.strptime(startDate.split("+")[0], "%Y-%m-%d"))
            #dd = time.mktime(time.strptime(startDate, "%Y-%m-%d"))
            startDate = time.strftime("%Y-%m-%dT00:00:00",time.localtime(dd))
           
            #try:
            dd2 = time.mktime(time.strptime(endDate, "%Y-%m-%d"))
            endDate = time.strftime("%Y-%m-%dT23:23:59",time.localtime(dd2))
            #except:
                #pass
            if github:
                max_records = 500
                page_size = 50
                startFound = False
                outList =[]
                topcommit = self.gettopCommit(self.module, self.branch, True)
                url =  "https://api.github.com/repos/greyorange/%s/commits?per_page=%d&sha=%s"%(self.module,page_size,topcommit)
                return self.parseOutGitHubDate(url,startDate,endDate,startFound,outList,max_records,page_size)
            else:
                startParsing = False
                startFound =False
                currentPage = 1
                outList =[]
                parse_out = self.parseOut(self.url,startDate,endDate,startParsing,startFound,outList,currentPage,raw)
            ###print(parse_out)
            return parse_out
        else:
            print("startdate should be less than enddate")
            
    def gitoutcommit(self,startcommit,endcommit, github = False):
        #print startDate,endDate
            
            startParsing = False
            startFound =False
            currentPage = 1
            outList =[]
            if github:
                max_records = 500
                page_size = 50
                url =  "https://api.github.com/repos/greyorange/%s/commits?per_page=%d&sha=%s"%(self.module,page_size,endcommit)
                return self.parseOutGitHub(url,startcommit,endcommit,startFound,outList,max_records,page_size)
            else:
                return self.parseOutCommit(self.url,startcommit,endcommit,startParsing,startFound,outList,currentPage)
    
    def parseOutGitHub(self,url,startCommit,endCommit,startFound,outList,max_records,page_size):
        #print(url,startCommit,endCommit,startParsing,startFound,outList,currentPage)
        print(url)
        out = self.getresult(url)
        revertList = []
        max_records -= page_size
        for itm in out:
            commit_raw = itm["sha"]
            if commit_raw == startCommit:
                startFound = True
                return outList,False,[]
            
            commit = commit_raw[:7]
            cdate = itm['commit']['committer']['date']
            msg = itm['commit']['message']
            summary = msg
            jiraList = self.getJirasGithub(msg)
            outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
            #print(commit_raw,startCommit)
            
        noChangeTag = []
        #print(outList,False,noChangeTag)
        if max_records <1:
            print("Max records %d expires , change the value or use right tags"%max_records)
            return False
        if not startFound :
            endCommit = commit_raw
            url =  "https://api.github.com/repos/greyorange/%s/commits?per_page=%d&sha=%s"%(self.module,page_size,endCommit)
            return self.parseOutGitHub(url,startCommit,endCommit,startFound, outList,max_records,page_size)
        
    def parseOutGitHubDate(self,url,startDate,endDate,startFound,outList,max_records,page_size):
        #print(url,startCommit,endCommit,startParsing,startFound,outList,currentPage)
        ##print(url)
        noChangeTag = []
        out = self.getresult(url)
        revertList = []
        max_records -= page_size
        for itm in out:
            cdate = itm['commit']['committer']['date']
            if startDate >= cdate:
                print(startDate ,cdate)
                startFound =True
                print(len(outList))
                print(outList,False,noChangeTag)
                return outList,False,[]
            if cdate <= endDate:
                #print(endDate ,cdate, itm)
                commit_raw = itm["sha"]
                commit = commit_raw[:7]
                msg = itm['commit']['message']
                summary = msg
                jiraList = self.getJirasGithub(msg)
                outList.append({"jira":jiraList,"summary":summary,"commit_id":commit,"date":cdate})
                #print(commit_raw,startCommit)
            
            
        
        #print(outList,False,noChangeTag)
        
        if max_records <1:
            print("Max records %d expires , change the value or use right tags"%max_records)
            return False
        if not startFound :
            endCommit = commit_raw
            url =  "https://api.github.com/repos/greyorange/%s/commits?per_page=%d&sha=%s"%(self.module,page_size,endCommit)
            return self.parseOutGitHubDate(url,startDate,endDate,startFound,outList,max_records,page_size)


if __name__=="__main__":
    apps = {
        "butler_server": "develop",
        "butler_remote": "develop",
        "butlerui": "develop",
        "greymatter-platform": "develop",
        "butler_interface": "develop",
        "wms-frontend": "develop",
        "wms-node": "develop",
        "gor-platform-transformer": "platform",
        "gor.reserve-picking.ui": "develop",
        "gor.butler.ui.ppsmodechange": "develop",
        "extractionapp": "develop",
        "gor.expectation.creator": "develop",
        "mdui": "master",
        "mdbff": "master",
        "towerui": "master",
        "tower": "master",
        "gups": "master",
        "asl": "master",
        "wmspackingapp": "develop",
        "gor.ui.mtuinduct": "develop",
        "ups": "master"
     }
    """
    for k, v in apps.items():
        r = releasenotes("amanseth91", "my2dCCFApkWUsfAkGqJ5", "release-6.2.0-new", "butler_server")
        top_commit = r.gettopCommit(k, v, github=False)
        get_tag = r.getTag(k, "6.2.0.2", github=False)
        print(get_tag)
    """
    #out = r.gitoutputdate("2022-06-28", "2022-07-01", False, True)
    #out = r.gettopCommit("butler_remote","develop",True)
    #out = r.gitoutcommit("9c6501baecb0878163fe363d1a762c3c33e916a5","736e9c6271b59d74c3e756eedeefd9735dae168b",True)
    #out = r.createBranch("butler_server","release-6.1.2", "025bf96886ab742880edc5716fba6fc091e7a9d8", True)
    ##out = r.deleteBranch("butler_server","test_6.1.0", True)
    #out = r.settag("butler_server", "6.6.6.6.6", "145c83ad57a35941dfd85fc37097f4cad025f2bd", True)
    #out = r.deleteTag("butler_server", "6.6.6.6.6", True)
    #myurl = "https://api.bitbucket.org/2.0/repositories/gorcode/butler_server/commit/26f3fb7e1547dd1c5577283295e5b97e1887b5b9"
    #print(r.getresult(myurl))
    
 