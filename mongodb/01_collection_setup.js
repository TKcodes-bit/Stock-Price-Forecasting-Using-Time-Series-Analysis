// Run in mongosh after selecting/creating the stock_timeseries database.
// One document represents one AAPL trading day. Market fields and derived
// indicators are embedded to keep time-series reads in one document.

const collectionName = "daily_stock_prices";

if (!db.getCollectionNames().includes(collectionName)) {
  db.createCollection(collectionName, {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["ticker", "company", "date", "market", "source"],
        properties: {
          ticker: { bsonType: "string", enum: ["AAPL"] },
          company: { bsonType: "string" },
          date: { bsonType: "date" },
          market: {
            bsonType: "object",
            required: ["open", "high", "low", "close", "volume"],
            properties: {
              open: { bsonType: ["double", "int", "long", "decimal"] },
              high: { bsonType: ["double", "int", "long", "decimal"] },
              low: { bsonType: ["double", "int", "long", "decimal"] },
              close: { bsonType: ["double", "int", "long", "decimal"] },
              volume: { bsonType: ["int", "long"] }
            }
          },
          indicators: {
            bsonType: "object",
            properties: {
              ma_20: { bsonType: ["double", "null", "int", "decimal"] },
              ma_50: { bsonType: ["double", "null", "int", "decimal"] },
              close_lag_1: { bsonType: ["double", "null", "int", "decimal"] },
              close_lag_5: { bsonType: ["double", "null", "int", "decimal"] },
              daily_return_pct: { bsonType: ["double", "null", "int", "decimal"] },
              absolute_return_pct: { bsonType: ["double", "null", "int", "decimal"] },
              rolling_volatility: { bsonType: ["double", "null", "int", "decimal"] }
            }
          },
          source: {
            bsonType: "object",
            required: ["dataset", "platform", "author", "file"],
            properties: {
              dataset: { bsonType: "string" },
              platform: { bsonType: "string" },
              author: { bsonType: "string" },
              file: { bsonType: "string" },
              url: { bsonType: "string" }
            }
          }
        }
      }
    },
    validationLevel: "strict",
    validationAction: "error"
  });
}

const prices = db.getCollection(collectionName);
prices.createIndex({ ticker: 1, date: -1 }, { unique: true, name: "uq_ticker_date" });
prices.createIndex({ date: 1 }, { name: "idx_trade_date" });
prices.createIndex({ "market.volume": -1 }, { name: "idx_volume_desc" });

print(`Collection ready: ${db.getName()}.${collectionName}`);
printjson(prices.getIndexes());
