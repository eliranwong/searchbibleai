class RefUtil:

    @staticmethod
    def getAllRefFilters(refs: list) -> dict:
        filters = []
        for ref in refs:
            filters += RefUtil.getRefFilter(ref)
        if filters and len(filters) == 1:
            return filters[0]
        elif filters and len(filters) > 1:
            return {"$or": filters}
        else:
            return {}

    @staticmethod
    def getRefFilter(ref: tuple) -> list:
        if len(ref) == 3:
            b, c, v = ref
            return [{"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": c}}, {"verse": {"$eq": v}}]}]
        elif len(ref) == 5:
            b, c, v, c2, v2 = ref
            if c == c2:
                return [{"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": c}}, {"verse": {"$gte": v}}, {"verse": {"$lte": v2}}]}]
            elif c2 > c:
                filter = []
                filter.append({"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": c}}, {"verse": {"$gte": v}}]})
                filter.append({"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": c2}}, {"verse": {"$lte": v2}}]})
                if (c2 - c) > 1:
                    for i in range(c+1, c2):
                        filter.append({"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": i}}]})
                return filter
        else:
            return []