CREATE TABLE complete_customer_details
AS
SELECT customers.id, 
       customers.name, 
       customer_purchases.product, 
       customer_purchases.price
FROM customers RIGHT JOIN customer_purchases
ON customers.id = customer_purchases.customer_id;