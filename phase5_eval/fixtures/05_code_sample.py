def normalize_scores(items):
    result = []
    for item in items:
        if "score" in item:
            if item["score"] > 100:
                item["score"] = 100
            if item["score"] < 0:
                item["score"] = 0
            result.append({"name": item.get("name"), "score": item["score"]})
        else:
            result.append(item)
    return result


def process(items, logger=None):
    values = normalize_scores(items)
    total = 0
    for value in values:
        total += value.get("score", 0)
    average = total / len(values)
    if logger:
        logger.info("average=%s", average)
    return {"items": values, "average": average}
