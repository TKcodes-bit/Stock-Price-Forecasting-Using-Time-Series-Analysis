// Run in mongosh after scripts/load_databases.py has populated the collection.
const prices = db.getCollection("daily_stock_prices");

// QUERY 1: Latest available AAPL trading observation.
print("QUERY 1 - latest AAPL observation");
printjson(
  prices.find({ ticker: "AAPL" })
        .sort({ date: -1 })
        .limit(1)
        .toArray()
);

// QUERY 2: AAPL observations between 8 and 14 February 2013 inclusive.
print("QUERY 2 - date range");
printjson(
  prices.find({
    ticker: "AAPL",
    date: {
      $gte: ISODate("2013-02-08T00:00:00Z"),
      $lt: ISODate("2013-02-15T00:00:00Z")
    }
  })
  .sort({ date: 1 })
  .toArray()
);

// QUERY 3: Full-period count, close-price range and average trading volume.
print("QUERY 3 - full-period summary");
printjson(
  prices.aggregate([
    { $match: { ticker: "AAPL" } },
    {
      $group: {
        _id: "$ticker",
        observation_count: { $sum: 1 },
        average_close: { $avg: "$market.close" },
        minimum_close: { $min: "$market.close" },
        maximum_close: { $max: "$market.close" },
        average_volume: { $avg: "$market.volume" }
      }
    },
    {
      $project: {
        _id: 0,
        ticker: "$_id",
        observation_count: 1,
        average_close: { $round: ["$average_close", 2] },
        minimum_close: 1,
        maximum_close: 1,
        average_volume: { $round: ["$average_volume", 2] }
      }
    }
  ]).toArray()
);

// Optional QUERY 4: Return the engineered features for January 2017.
print("OPTIONAL QUERY 4 - technical indicators by date range");
printjson(
  prices.find({
    ticker: "AAPL",
    date: {
      $gte: ISODate("2017-01-01T00:00:00Z"),
      $lt: ISODate("2017-02-01T00:00:00Z")
    }
  }, {
    _id: 0,
    date: 1,
    "market.close": 1,
    indicators: 1
  }).sort({ date: 1 }).toArray()
);
