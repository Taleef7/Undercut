INSERT INTO dim_tyre_compound (tyre_compound_id, compound_label, compound_category, compound_code, compound_hardness_order, is_wet, is_intermediate, is_slick) VALUES
('SOFT', 'Soft', 'slick', 'S', 1, FALSE, FALSE, TRUE),
('MEDIUM', 'Medium', 'slick', 'M', 2, FALSE, FALSE, TRUE),
('HARD', 'Hard', 'slick', 'H', 3, FALSE, FALSE, TRUE),
('INTERMEDIATE', 'Intermediate', 'wet', 'I', 4, FALSE, TRUE, FALSE),
('WET', 'Wet', 'wet', 'W', 5, TRUE, FALSE, FALSE),
('C1', 'C1', 'slick', 'C1', 1, FALSE, FALSE, TRUE),
('C2', 'C2', 'slick', 'C2', 2, FALSE, FALSE, TRUE),
('C3', 'C3', 'slick', 'C3', 3, FALSE, FALSE, TRUE),
('C4', 'C4', 'slick', 'C4', 4, FALSE, FALSE, TRUE),
('C5', 'C5', 'slick', 'C5', 5, FALSE, FALSE, TRUE);
