from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

class HFLLM:
    def __init__(self, model="microsoft/Phi-3-mini-4k-instruct"):
        self.tokenizer = AutoTokenizer.from_pretrained(model)

        quant_config = BitsAndBytesConfig(load_in_8bit=True)

        self.model = AutoModelForCausalLM.from_pretrained(
            model,
            quantization_config=quant_config,
            device_map="auto"
        )

    def generate(self, prompt, max_tokens=200):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0
        )
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
