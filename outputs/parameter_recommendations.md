# Recommended Parameters for a Grounded RAG Assistant

## Objective

Choose generation settings that encourage concise, factual answers
while controlling response length and unnecessary token usage.

## 1. Temperature

Recommended starting value: 0.0–0.2

A low temperature reduces randomness in token selection and is a
sensible starting point for factual question answering.

It does not guarantee factual accuracy. The assistant must still
be grounded in retrieved documents and instructed not to invent facts.

## 2. Maximum Output Tokens

Recommended starting value: 150–300 tokens

The output limit should be long enough to answer typical staff
questions but short enough to discourage unnecessarily long answers.

A very small limit may truncate an answer before it is complete.
The appropriate value depends on the expected response length.

## 3. Top-p

Recommended starting value: 1.0

Top-p controls nucleus sampling by restricting the set of candidate
tokens according to their cumulative probability.

Keeping top-p at 1.0 initially allows us to study temperature
without simultaneously changing another sampling parameter.

## Recommended Initial Configuration

- temperature: 0.1
- max_tokens: 200
- top_p: 1.0

These values are starting points, not experimentally validated
optimal settings. They should be tested against representative
questions and evaluated for accuracy, completeness, and cost.

## Conclusion

For a grounded RAG assistant, I would start with a low temperature,
a sensible output-token limit, and top_p set to 1.0.

I would then evaluate the results on representative questions
before finalizing the configuration.