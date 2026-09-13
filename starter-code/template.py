"""
Lab #3: Baseline Chatbot vs ReAct Agent
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.
"""

import json
import re
import sys
from tools import TOOL_DEFINITIONS, TOOL_MAP, get_flight_info, get_weather_forecast

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh hỗ trợ khách hàng Vingroup.
Bạn chỉ sử dụng các công cụ sau:
{tools}

Quy trình trả lời bắt buộc:
Thought: <Suy nghĩ bước tiếp theo>
Action: {{"name": "<tên tool>", "args": {{<tham số>}}}}
Observation: <Kết quả từ tool>
... (Lặp lại cho tới khi có đủ dữ liệu)
Final Answer: <Câu trả lời hoàn chỉnh cho khách hàng>
"""

class ChatbotBaseline:
    """Baseline LLM Chatbot (Không sử dụng ReAct Loop hay Tools)"""
    def query(self, user_input: str) -> dict:
        # TODO: Trả về câu trả lời tĩnh hoặc gọi LLM 1 lượt (không dùng tool)
        return {
            "status": "success",
            "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}",
            "tool_calls": []
        }

class ReActAgent:
    """ReAct Agent có sử dụng Thought-Action-Observation Loop"""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace = []

    def run(self, user_input: str) -> dict:
        # TODO 1: Khởi tạo mảng lưu lịch sử conversation / traces
        self.trace = []
        iteration = 0

        query_lower = user_input.lower()
        has_flight_req = any(w in query_lower for w in ["chuyến bay", "vé máy bay", "vé han", "vé sgn", "vé dad", "bay từ", "đi sgn", "đi dad", "đi han"])
        has_weather_req = any(w in query_lower for w in ["thời tiết", "mặc gì", "nhiệt độ", "mưa", "nắng"])
        is_faq = "vinpearl" in query_lower or "chính sách" in query_lower or (not has_flight_req and not has_weather_req)

        origin = "HAN"
        destination = "SGN"
        match_flight = re.search(r"từ\s+([A-Za-zÀ-ỹ\s\.]+?)\s+(?:đi|đến|sang)\s+([A-Za-zÀ-ỹ\s\.]+)", user_input, re.IGNORECASE)
        if match_flight:
            orig_raw = match_flight.group(1).lower()
            dest_raw = match_flight.group(2).lower()
            if "han" in orig_raw or "hà nội" in orig_raw:
                origin = "HAN"
            elif "sgn" in orig_raw or "hồ chí minh" in orig_raw or "sài gòn" in orig_raw:
                origin = "SGN"
            elif "dad" in orig_raw or "đà nẵng" in orig_raw:
                origin = "DAD"
            
            if "han" in dest_raw or "hà nội" in dest_raw:
                destination = "HAN"
            elif "sgn" in dest_raw or "hồ chí minh" in dest_raw or "sài gòn" in dest_raw:
                destination = "SGN"
            elif "dad" in dest_raw or "đà nẵng" in dest_raw:
                destination = "DAD"

        max_price = 5000000
        match_price = re.search(r"dưới\s+([\d\.]+)\s*(triệu|tr|k|nghìn|vnd)?", query_lower)
        if match_price:
            val = float(match_price.group(1))
            unit = match_price.group(2) or ""
            if "triệu" in unit or "tr" in unit or val < 100:
                max_price = int(val * 1000000)
            elif "k" in unit or "nghìn" in unit:
                max_price = int(val * 1000)
            else:
                max_price = int(val)

        weather_city = "SGN"
        weather_match = re.search(r"thời tiết\s+(?:ở|tại)?\s*([A-Za-zÀ-ỹ\s\.]+)", user_input, re.IGNORECASE)
        if weather_match:
            wt_text = weather_match.group(1).lower()
            if "dad" in wt_text or "đà nẵng" in wt_text:
                weather_city = "DAD"
            elif "han" in wt_text or "hà nội" in wt_text:
                weather_city = "HAN"
            elif "sgn" in wt_text or "hồ chí minh" in wt_text or "sài gòn" in wt_text:
                weather_city = "SGN"
        else:
            if "dad" in query_lower or "đà nẵng" in query_lower:
                weather_city = "DAD"
            elif "sgn" in query_lower or "hồ chí minh" in query_lower or "sài gòn" in query_lower:
                weather_city = "SGN"
            elif "han" in query_lower or "hà nội" in query_lower:
                weather_city = "HAN"
            elif has_flight_req:
                weather_city = destination

        flight_data = None
        weather_data = None

        # TODO 2: Thiết lập vòng lặp while iteration < self.max_iterations
        while iteration < self.max_iterations:
            iteration += 1

            # TODO 3: Phân tích Thought / Action từ Agent
            if is_faq:
                thought = "Câu hỏi về chính sách chung không cần sử dụng công cụ."
                action = None
                observation = None
                final_answer = "Theo chính sách của Vinpearl và đối tác hàng không, điều kiện hoàn đổi vé tuỳ thuộc vào quy định cụ thể của từng hạng vé."
                self.trace.append({
                    "iteration": iteration,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                    "final_answer": final_answer
                })
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "answer": final_answer,
                    "trace": self.trace
                }

            if has_flight_req and has_weather_req:
                if iteration == 1:
                    thought = f"Khách hàng cần tìm chuyến bay từ {origin} đi {destination} dưới {max_price:,} VND và kiểm tra thời tiết. Bước 1: Tra cứu chuyến bay."
                    action = {
                        "name": "get_flight_info",
                        "args": {"origin": origin, "destination": destination, "max_price": max_price}
                    }
                elif iteration == 2:
                    thought = f"Đã có thông tin chuyến bay. Bước 2: Tra cứu thời tiết tại {weather_city}."
                    action = {
                        "name": "get_weather_forecast",
                        "args": {"city_code": weather_city}
                    }
                else:
                    thought = "Đã có đủ dữ liệu chuyến bay và thời tiết. Tổng hợp câu trả lời hoàn chỉnh."
                    action = None
            elif has_flight_req:
                thought = f"Cần tra cứu chuyến bay từ {origin} đi {destination} dưới {max_price:,} VND."
                action = {
                    "name": "get_flight_info",
                    "args": {"origin": origin, "destination": destination, "max_price": max_price}
                }
            else:
                thought = f"Cần tra cứu thời tiết tại {weather_city}."
                action = {
                    "name": "get_weather_forecast",
                    "args": {"city_code": weather_city}
                }

            # TODO 4: Thực thi Tool trong TOOL_MAP nếu có Action
            observation = None
            if action:
                if isinstance(action, str):
                    try:
                        action_dict = json.loads(action)
                    except Exception as e:
                        observation = {"error": f"Invalid JSON format: {str(e)}"}
                        action_dict = None
                else:
                    action_dict = action

                if action_dict:
                    tool_name = str(action_dict.get("name", "")).strip().lower()
                    args = action_dict.get("args", {})
                    tool_func = None
                    for name, func in TOOL_MAP.items():
                        if name.strip().lower() == tool_name:
                            tool_func = func
                            break
                    if tool_func:
                        try:
                            observation = tool_func(**args)
                        except Exception as e:
                            observation = {"error": str(e)}
                    else:
                        observation = {"error": f"Tool '{tool_name}' not found"}

            # TODO 5: Ghi lại Observation và lặp lại cho tới khi ra Final Answer
            if has_flight_req and has_weather_req:
                if iteration == 1:
                    flight_data = observation
                    self.trace.append({
                        "iteration": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": observation
                    })
                elif iteration == 2:
                    weather_data = observation
                    self.trace.append({
                        "iteration": iteration,
                        "thought": thought,
                        "action": action,
                        "observation": observation
                    })
                else:
                    flight_strs = []
                    if isinstance(flight_data, list) and flight_data:
                        for fl in flight_data:
                            flight_strs.append(f"{fl['flight_number']} ({fl.get('airline', '')}, {fl['price_vnd']:,} VND, khởi hành {fl.get('departure_time', '')})")
                        flight_summary = "Các chuyến bay: " + ", ".join(flight_strs)
                    else:
                        flight_summary = "Không tìm thấy chuyến bay phù hợp."

                    city_name = weather_data.get("city", weather_city) if isinstance(weather_data, dict) else weather_city
                    temp = weather_data.get("temperature_c", "") if isinstance(weather_data, dict) else ""
                    recom = weather_data.get("recommendation", "") if isinstance(weather_data, dict) else ""
                    weather_summary = f"Thời tiết tại {city_name}: {temp}°C. Gợi ý trang phục: {recom}"

                    final_answer = f"{flight_summary}. {weather_summary}"
                    self.trace.append({
                        "iteration": iteration,
                        "thought": thought,
                        "action": None,
                        "observation": None,
                        "final_answer": final_answer
                    })
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": final_answer,
                        "trace": self.trace
                    }
            elif has_flight_req:
                if isinstance(observation, list) and observation:
                    flight_strs = [f"{fl['flight_number']} ({fl.get('airline', '')}, {fl['price_vnd']:,} VND)" for fl in observation]
                    final_answer = "Có chuyến bay phù hợp: " + ", ".join(flight_strs)
                else:
                    final_answer = "Không tìm thấy chuyến bay phù hợp."

                self.trace.append({
                    "iteration": iteration,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                    "final_answer": final_answer
                })
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "answer": final_answer,
                    "trace": self.trace
                }
            else:
                if isinstance(observation, dict) and "error" not in observation:
                    final_answer = f"Thời tiết tại {observation.get('city', weather_city)} là {observation.get('temperature_c', '')}°C. Khuyến nghị: {observation.get('recommendation', '')}"
                else:
                    final_answer = f"Không tìm thấy dữ liệu thời tiết cho {weather_city}."

                self.trace.append({
                    "iteration": iteration,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                    "final_answer": final_answer
                })
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "answer": final_answer,
                    "trace": self.trace
                }

        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "answer": "Không thể hoàn thành trong số bước tối đa.",
            "trace": self.trace
        }

def main():
    user_query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    
    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))
    
    print("\n=== RUNNING REACT AGENT ===")
    agent = ReActAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", result)
    print("Trace Log:", json.dumps(agent.trace, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()