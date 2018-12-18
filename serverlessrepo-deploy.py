#!/usr/bin/env python3
import boto3
import botocore.exceptions
import subprocess
import sys

import time
import yaml
import urllib.request


def get_application(serverlessrepo, application_name):
    list_applications_result = serverlessrepo.list_applications()
    for application in list_applications_result["Applications"]:
        if application["Name"] == application_name:
            return serverlessrepo.get_application(ApplicationId=application["ApplicationId"])
    next_token = list_applications_result.get("NextToken")
    while next_token:
        list_applications_result = serverlessrepo.list_applications(NextToken=next_token)
        for application in list_applications_result["Applications"]:
            if application["Name"] == application_name:
                return serverlessrepo.get_application(ApplicationId=application["ApplicationId"])
        next_token = list_applications_result.get("NextToken")
    return None


def main():
    config_yaml_file = open("serverlessrepo.yaml")
    config_yaml_str = config_yaml_file.read()
    config_yaml_file.close()
    config = yaml.load(config_yaml_str)

    print("Installing dependencies...")
    subprocess.check_call(
        ["npm", "install"], cwd="./src/api/convert"
    )

    print("Packaging template...")
    packaged_template_yaml = subprocess.check_output(
        ["aws", "cloudformation", "package", "--profile", config["AWSProfile"], "--template-file", "template.yaml",
         "--s3-bucket", config["S3Bucket"]]
    ).decode().split("\n", 1)[1]

    session = boto3.Session(profile_name=config["AWSProfile"])

    serverlessrepo = session.client("serverlessrepo", region_name=config["Region"])
    application = get_application(serverlessrepo, config["Name"])

    readme_md_file = open("README.md")
    readme_md_str = readme_md_file.read()
    readme_md_file.close()

    license_txt_file = open("LICENSE")
    license_txt_str = license_txt_file.read()
    license_txt_file.close()

    if application:
        old_license_txt_str = urllib.request.urlopen(application["LicenseUrl"]).read().decode()
        if old_license_txt_str == license_txt_str and config["SpdxLicenseId"] == application["SpdxLicenseId"]:
            print("Updating application...")
            application = serverlessrepo.update_application(
                ApplicationId=application["ApplicationId"],
                Author=config["Author"],
                Description=config["Description"],
                HomePageUrl=config["HomePageUrl"],
                Labels=config["Labels"],
                ReadmeBody=readme_md_str
            )
        else:
            print("License of existing application cannot be updated!")
            sys.exit(1)

    else:
        print("Creating application...")
        application = serverlessrepo.create_application(
            Name=config["Name"],
            Author=config["Author"],
            Description=config["Description"],
            HomePageUrl=config["HomePageUrl"],
            Labels=config["Labels"],
            ReadmeBody=readme_md_str,
            SpdxLicenseId=config["SpdxLicenseId"],
            LicenseBody=license_txt_str
        )
    print("Creating application version...")
    try:
        serverlessrepo.create_application_version(
            ApplicationId=application["ApplicationId"],
            SemanticVersion=config["SemanticVersion"],
            SourceCodeUrl=config["SourceCodeUrl"],
            TemplateBody=packaged_template_yaml
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print("Cannot update existing application version!")
            sys.exit(1)
        else:
            raise e

    if config["public"]:
        print("Making application public...")
        try:
            time.sleep(5)
            serverlessrepo.put_application_policy(
                ApplicationId=application["ApplicationId"],
                Statements=[
                    {
                        "Actions": [
                            "Deploy",
                        ],
                        "Principals": [
                            "*",
                        ],
                        "StatementId": "PublicAccess"
                    },
                ]
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'BadRequestException':
                print("Cannot make application public: %s" % e.response['Error']['Message'])
                pass
            else:
                raise e


if __name__ == "__main__":
    main()
