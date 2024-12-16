grammar minipy3;

// 解析器规则（Parser Rules）
program: (statement NEWLINE | NEWLINE)* EOF;
statement: simpleStmt | compoundStmt;
simpleStmt: assignmentStmt | returnStmt;
compoundStmt: ifStmt | whileStmt | forStmt | funcDef;
assignmentStmt: IDENTIFIER ASSIGN expression | arrayMember ASSIGN expression;
returnStmt: RETURN expression?;
ifStmt: IF condition COLON NEWLINE program (elifStmt | elseStmt)?;
elifStmt: ELIF condition COLON NEWLINE program (elifStmt | elseStmt)?;
elseStmt: ELSE COLON NEWLINE program;
whileStmt: WHILE condition COLON NEWLINE program;
forStmt: FOR IDENTIFIER IN expression COLON NEWLINE program;
funcDef: DEF IDENTIFIER LPAREN parameters? RPAREN COLON NEWLINE program;
parameters: IDENTIFIER (COMMA IDENTIFIER)*;

condition: logicExpr;
logicExpr: comparison (logicOp comparison)*;
comparison: NOT comparison | algebraicExpr (conditionOp algebraicExpr)?;
logicOp: AND | OR;
expression: algebraicExpr | STRING_LITERAL | list | TRUE | FALSE;
algebraicExpr: term termTail;
termTail: (PLUS term termTail) | (MINUS term termTail) | ;
term: factor factorTail;
factorTail: (MULTIPLY factor factorTail) | (DIVIDE factor factorTail) | ;
factor: IDENTIFIER | NUMBER | LPAREN algebraicExpr RPAREN | funcCall | arrayMember;

funcCall: IDENTIFIER LPAREN (expression (COMMA expression)*)? RPAREN;
list: LBRACKET (expression (COMMA expression)*)? RBRACKET;
arrayMember: IDENTIFIER LBRACKET expression RBRACKET;

// 词法规则（Lexer Rules）
RETURN: 'return';
IF: 'if';
ELIF: 'elif';
ELSE: 'else';
WHILE: 'while';
FOR: 'for';
IN: 'in';
DEF: 'def';
AND: 'and';
OR: 'or';
NOT: 'not';
ASSIGN: '=';
COLON: ':';
COMMA: ',';
PLUS: '+';
MINUS: '-';
MULTIPLY: '*';
DIVIDE: '//';
LPAREN: '(';
RPAREN: ')';
LBRACKET: '[';
RBRACKET: ']';
TRUE: 'True';
FALSE: 'False';
NEWLINE: '\r'? '\n' INDENT?;
INDENT: ('\t')+;
WS: [ \t]+ -> skip;

conditionOp: '==' | '!=' | '>' | '<' | '>=' | '<=';
IDENTIFIER: [a-zA-Z_][a-zA-Z0-9_]*;
NUMBER: '-'? [0-9]+ ('.' [0-9]+)?;
STRING_LITERAL: 
    ('"' (~["\r\n] | '""')* '"') 
    | 
    ('\'' (~['\r\n] | '\'\'')* '\'');