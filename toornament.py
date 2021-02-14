import datetime
import json
import parse
import pause
import requests

class ToornamentAPI:


    # Constructor
    # authorization: Authorization self object
    # mysql: MySQL wrapper object
    # overwrite: If set to True, existing tables will be dropped and overwritten
    def __init__(self, auth_path: str):
        self.__api_cooldown = datetime.datetime.now()
        self.__time_per_request = 333

        self.__credential_path = auth_path
        self.__load_api_credentials()

        self.__group_buffer = {}
        self.__tournament_buffer = {}


    def __load_api_credentials(self):
        "Loads the Toornament API credentials from a given JSON-file."

        with open(self.__credential_path, 'r', encoding='utf-8') as token_file:
            self.__credentials = json.load(token_file)
            self.__credentials["auth_expiry"] = datetime.datetime.strptime(self.__credentials["auth_expiry"], "%d.%m.%Y, %H:%M:%S")

    def __update_api_credentials(self, response):
        "Updates the local Toornament API credentials and overwrites the JSON-file they were loaded from."

        self.__credentials["auth_key"] = response["access_token"]
        self.__credentials["auth_type"] = response["token_type"]
        self.__credentials["auth_scope"] = response["scope"]

        expiry_in_seconds = response["expires_in"]
        auth_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expiry_in_seconds - 10)
        self.__credentials["auth_expiry"] = auth_expiry.strftime("%d.%m.%Y, %H:%M:%S")

        with open(self.__credential_path, 'w', encoding='utf-8') as credential_file:
            json.dump(self.__credentials, credential_file, indent=2)

        self.__credentials["auth_expiry"] = auth_expiry
    
    def __has_api_token_expired(self):
        "Checks if the Toornament authorization token has already expired or not."

        # Adds 1 minute to current time to avoid key expiry mid-operation
        # (e.g. this method returns False but 10ms later the token expires before the API call is made)
        if datetime.datetime.now() + datetime.timedelta(minutes = 1) > self.__credentials["auth_expiry"]:
            return True
        else:
            return False

    def __check_auth_token(self):
        "Checks if the Toornament authorization key is up-to-date. Requests and saves a new one if not."

        if self.__has_api_token_expired():

            # Requests new authorization token from OAuth2 endpoint
            # See: https://developer.toornament.com/v2/doc/security_oauth2#post:oauthv2token
            request_url = "https://api.toornament.com/oauth/v2/token"

            request_headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            request_data = {
                "grant_type": "client_credentials",
                "scope": "organizer:participant organizer:result",
                "client_id": self.__credentials["client_id"],
                "client_secret": self.__credentials["client_secret"]
            }

            response = self.__request_post(url = request_url, data = request_data, headers = request_headers, authorization=False)
            self.__update_api_credentials(response)


    # Checks the time since the last endpoint call and cools down if necessary.
    # Currently a rate limit of 3 calls/second is used. (This is implemented as a 0.333sec minimum cooldown)
    def __respect_rate_limits(self):
        if datetime.datetime.now() < self.__api_cooldown:
            pause.until(self.__api_cooldown)
        
        self.__api_cooldown = datetime.datetime.now() + datetime.timedelta(milliseconds=self.__time_per_request)


    # Sends a GET request to a toornament API endpoint. Takes care of authorization&API tokens, rate limits and response validation.
    # url: The API endpoint URL
    # headers: The additional headers to be provided to the API. Authorization and API-Token are added automatically by this method and must not be given to it manually!
    # authorization: If this is True, the method will refresh the OAuth2 authorization token and add it to the request header
    def __request_get(self, url: str, headers = {}, authorization: bool = False):
        # Updates OAuth2 authorization and adds the token to the headers
        if authorization:
            self.__check_auth_token()
            headers['Authorization'] = self.__credentials["auth_key"]
        
        # Adds API-token to header
        headers['X-Api-Key'] = self.__credentials["token"]
        
        # Respects rate limits
        self.__respect_rate_limits()

        # Sends GET request
        response = requests.get(url = url, headers = headers)

        # Returns response as JSON if it is OK
        if response.ok:
            return response.json()
        else:
            raise response.raise_for_status()


    # Sends a POST request to a toornament API endpoint. Takes care of authorization&API tokens, rate limits and response validation.
    # url: The API endpoint URL
    # data: The data to be sent with the request
    # headers: The additional headers to be provided to the API. Authorization and API-Token are added automatically by this method and must not be given to it manually!
    # authorization: If this is True, the method will refresh the OAuth2 authorization token and add it to the request header
    def __request_post(self, url: str, data = None, headers = {}, authorization: bool = False):
        
        # Updates OAuth2 authorization and adds the token to the headers
        if authorization:
            self.__check_auth_token()
            headers['Authorization'] = self.__credentials["auth_key"]
        
        # Adds API-token to header
        headers['X-Api-Key'] = self.__credentials["token"]
        
        # Respects rate limits
        self.__respect_rate_limits()

        # Sends POST request
        response = requests.post(url = url, data = data, headers = headers)

        # Returns response as JSON if it is OK
        if response.ok:
            return response.json()
        else:
            raise response.raise_for_status()


    # Retrieves multiple pages of content via GET-requests and returns them as one result.
    # More infos about pagination: https://developer.toornament.com/v2/overview/pagination
    # url: The API endpoint URL
    # headers: The additional headers to be provided to the API. Authorization, API-token and range are added automatically and must not be given manually!
    # authorization: If this is True, the method will refresh the OAuth2 authorization token and add it to the request header
    # unit: The unit in which the paginated content is counted (e.g. tournaments, items, participants, etc)
    # itemsPerRequest: How many items can be requested per page. Consult toornament API documentation to get the right number for your API endpoint.
    def __request_get_pages(self, url: str, headers = {}, authorization: bool =  False, unit: str = "items", items_per_request: int = 50):
    
        # Updates OAuth2 authorization and adds the token to the headers
        if authorization:
            self.__check_auth_token()
            headers['Authorization'] = self.__credentials["auth_key"]
        
        # Adds API-token to header
        headers['X-Api-Key'] = self.__credentials["token"]

        # Defines Content-Range return format used to determine if the last page is reached
        content_range_format = f"{unit} {{:d}}-{{:d}}/{{:d}}"
        page_start = 0
        total_page_num = 1
        page_list = []

        while page_start < total_page_num:
            # Adds updated range to header
            page_end = page_start + items_per_request - 1
            headers['Range'] = f"{unit}={page_start}-{page_end}"

            # Respect rate limit
            self.__respect_rate_limits()

            # Request next set of pages
            response = requests.get(url = url, headers = headers)

            if response.ok:
                # Adds new pages to the full collection
                page_list += response.json()

                # Retrieve information on how many pages are left from response headers
                content_range_str = response.headers['Content-Range']
                parsed_content_range = parse.parse(content_range_format, content_range_str)

                # If no content is returned, leave the loop
                if parsed_content_range is None:
                    break

                last_page_index = parsed_content_range[1]
                total_page_num = parsed_content_range[2]

                # Calculates which is the next page to be retrieved
                page_start = last_page_index + 1
            else:
                response.raise_for_status()

        return page_list

    



    def get_ranking(self, tournament_id, stage_id, group_id = ""):

        request_url  = f"https://api.toornament.com/viewer/v2/tournaments/{tournament_id}/stages/{stage_id}/ranking-items"
        request_url += f"?group_ids={group_id}"

        ranking = self.__request_get_pages(request_url)
        # ranking = sorted(ranking, key = lambda team: team["position"])[::-1] # This line would sort the ranking in the same order as displayed on Toornament. This seems to be done automatically though.
        
        return ranking


    def get_matches(self, tournament_id, stage_id, group_id = "", round_nums = []):

        if not isinstance(round_nums, list):
            round_nums = [round_nums]

        round_nums = [str(round_num) for round_num in round_nums]

        request_url  = f"https://api.toornament.com/viewer/v2/tournaments/{tournament_id}/matches"
        request_url += f"?stage_ids={stage_id}&group_ids={group_id}&round_numbers={','.join(round_nums)}"

        matches = self.__request_get_pages(request_url, unit="matches")

        return matches

    
    def get_groups(self, tournament_id):

        request_url = f"https://api.toornament.com/viewer/v2/tournaments/{tournament_id}/groups"
        groups = self.__request_get_pages(request_url, unit="groups")

        return groups


    def get_stage(self, tournament_id, stage_id):
        
        request_url = f"https://api.toornament.com/viewer/v2/tournaments/{tournament_id}/stages/{stage_id}"
        stage = self.__request_get(request_url)

        return stage

    
    def get_tournament(self, tournament_id):

        if tournament_id in self.__tournament_buffer:
            return self.__tournament_buffer[tournament_id]

        request_url = f"https://api.toornament.com/viewer/v2/tournaments/{tournament_id}"
        tournament = self.__request_get(request_url)

        self.__tournament_buffer[tournament_id] = tournament

        return tournament


    def get_group_info(self, tournament_id, group_name):

        if tournament_id in self.__group_buffer:
            groups = self.__group_buffer[tournament_id]
        else:
            groups = self.get_groups(tournament_id)
            self.__group_buffer[tournament_id] = groups

        for group in groups:
            if group["name"] == group_name:
                group["tournament_id"] = tournament_id
                return group

        return None