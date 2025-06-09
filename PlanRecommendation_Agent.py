# Databricks notebook source
import mlflow.deployments
import json

class InputParserAgent:
    def __init__(self, endpoint):
        self.client = mlflow.deployments.get_deploy_client("databricks")
        self.endpoint = endpoint

    def run(self, user_input: str) -> dict:
        system_prompt = """
You are a healthcare assistant that extracts structured information from user input for Medicare recommendations.

Return a JSON object with the following fields:
- conditions: list of medical conditions (e.g., diabetes, heart disease)
- location: object with 'city' and 'state' fields

Only return valid JSON. Do not include explanations or extra text.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response = self.client.predict(
            endpoint=self.endpoint,
            inputs={"messages": messages}
        )

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        try:
            parsed = json.loads(content)
            if not all(k in parsed for k in ["conditions", "location"]):
                raise ValueError("Missing required fields in response.")
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": f"Failed to parse response: {str(e)}", "raw_response": content}

# COMMAND ----------

from pyspark.sql import SparkSession
import json
import requests
import mlflow.deployments

class MedicareInputAgent:
    def __init__(self, user_profile,endpoint):
        self.spark = SparkSession.builder.getOrCreate()
        self.user_profile = user_profile
        self.client = mlflow.deployments.get_deploy_client("databricks")
        self.endpoint = endpoint

        # Extract required fields from JSON input
        self.user_state = user_profile.get("state")
        self.user_county = user_profile.get("county")
        self.user_condition = user_profile.get("conditions", [None])[0]
        #self.coverage_needs = user_profile.get("coverage_needs", [])
        #self.needs_dental = "dental" in self.coverage_needs
        self.filtered_plans = []

    def filter_plans(self):
        query = f"""
        SELECT DISTINCT
            plan_id,
            cpsc_plan_name,
            part_d_total_premium,
            chronic_condition,
            overall_star_rating
        FROM neugold.default.recommended_plans
        WHERE plan_state = '{self.user_state}'
          AND plan_county = '{self.user_county}'
          AND chronic_condition LIKE '%{self.user_condition}%'
        ORDER BY overall_star_rating DESC, part_d_total_premium ASC
        """
        # print(query)
        df = self.spark.sql(query)
        self.filtered_plans = [row.asDict() for row in df.collect()]
        #print(self.filtered_plans)

    def build_prompt(self):
        return f"""
User Profile:
- State: {self.user_state}
- County: {self.user_county}
- Health Conditions: {', '.join(self.user_profile.get('conditions', []))}

Available Plans:
{json.dumps(self.filtered_plans, indent=2)}

Instructions:
- Recommend the top 2–3 plans.
- Explain why each plan is a good fit.
- Mention trade-offs.
- Be clear and helpful.
"""
    def build_sys_prompt(self):
        return  """
You are a helpful and knowledgeable Medicare plan advisor.

Your task is to recommend the best Medicare plans based on the user's profile and a list of available plans.

The user's profile includes:
- State and county of residence
- A list of health conditions (e.g., diabetes, heart disease)
- A list of coverage needs (e.g., dental, vision, prescription drugs)

You will be provided with a list of available plans in JSON format. Each plan includes:
- Plan name
- Premium cost
- Chronic condition coverage
- Overall star rating

Your response must:
- Recommend the top 2–3 plans
- Explain why each plan is a good fit for the user
- Mention any trade-offs (e.g., higher cost for better coverage)
- Be clear, concise, and helpful

Do not include disclaimers or follow-up questions. Only respond with the recommendation.
"""


    def get_recommendation(self):
        prompt = self.build_prompt()
        system_prompt=self.build_sys_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.client.predict(
            endpoint=self.endpoint,
            inputs={"messages": messages}
        )
        return response
        # Adjust based on your API's response format
        # recommendation = response.get("text", "No response received.")
        # print("🧠 Plan Recommendation:\n")
        # print(recommendation)


# COMMAND ----------

import json

class MedcareAgent:    
    def get_medicare_plans(self, user_input):
        endpoint_url = "databricks-meta-llama-3-1-8b-instruct"
        agent = InputParserAgent(endpoint=endpoint_url)
       
        result = agent.run(user_input)
        print(result)
        input_dict = json.loads(json.dumps(result))

        user_profile = {
            "state": input_dict["location"]["state"],
            "county": input_dict["location"]["city"],
            "conditions": input_dict["conditions"]
        }

        print(user_profile)

        agent = MedicareInputAgent(user_profile, endpoint_url)
        agent.filter_plans()
        import re

        response = agent.get_recommendation()

        content = response['choices'][0]['message']['content']
        return content

# COMMAND ----------

 user_input = "I'm 67 Female, live in Washington, NE, and need coverage for lung issues."
agent = MedcareAgent()
response = agent.get_medicare_plans(user_input)
print(response)



# COMMAND ----------

# if response and 'choices' in response and response['choices']:
#     content = response['choices'][0]['message']['content']
#     print(content)
print(response)